from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from flask import Blueprint, abort, current_app, jsonify, request
from sqlalchemy import select

from .database import session_scope
from .external import WebhookError, dispatch_to_backend
from .models import ChatSession, Message, Sender
from .security import generate_player_identifier, is_end_of_conversation, normalise_player, validate_message

api_bp = Blueprint("api", __name__)


def _load_session(db, session_token: str) -> ChatSession | None:
    stmt = select(ChatSession).where(ChatSession.session_token == session_token)
    return db.execute(stmt).scalar_one_or_none()


@api_bp.post("/session")
def create_session():
    payload = request.get_json(silent=True) or {}
    requested_player = normalise_player(payload.get("player"))

    if not requested_player:
        requested_player = generate_player_identifier()

    session_token = uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + current_app.config["SESSION_TTL"]

    with session_scope() as db:
        chat_session = ChatSession(session_token=session_token, player_id=requested_player)
        db.add(chat_session)

    current_app.logger.info(
        "Sessao criada",
        extra={
            "event": "session.created",
            "session_token": session_token,
            "player": requested_player,
        },
    )

    return (
        jsonify(
            {
                "session_token": session_token,
                "player": requested_player,
                "expires_at": expires_at.isoformat(),
            }
        ),
        201,
    )


@api_bp.get("/messages")
def list_messages():
    session_token = request.args.get("session_token")
    if not session_token:
        abort(400, "session_token eh obrigatorio")

    with session_scope(session_identifier=session_token) as db:
        chat_session = _load_session(db, session_token)
        if chat_session is None:
            abort(404, "Sessao nao encontrada")

        stmt = (
            select(Message)
            .where(Message.session_token == session_token)
            .order_by(Message.created_at.asc())
        )
        rows = db.execute(stmt).scalars().all()
        messages = [
            {
                "id": message.id,
                "sender": message.sender.value,
                "content": message.content,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in rows
        ]
        response = {
            "messages": messages,
            "is_active": chat_session.is_active,
        }

    current_app.logger.debug(
        "Mensagens listadas",
        extra={
            "event": "messages.listed",
            "session_token": session_token,
            "count": len(messages),
            "active": response["is_active"],
        },
    )

    return jsonify(response)


@api_bp.post("/messages")
def send_message():
    payload = request.get_json(silent=True) or {}
    session_token = payload.get("session_token")
    player = normalise_player(payload.get("player"))

    if not session_token:
        abort(400, "session_token eh obrigatorio")
    if not player:
        abort(400, "player invalido")

    try:
        message_text = validate_message(payload.get("message"))
    except ValueError as exc:
        abort(400, str(exc))

    sent_at = datetime.now(timezone.utc)
    player_payload = {
        "sender": Sender.PLAYER.value,
        "content": message_text,
        "created_at": sent_at.isoformat(),
    }

    with session_scope(session_identifier=session_token) as db:
        chat_session = _load_session(db, session_token)
        if chat_session is None:
            abort(404, "Sessao nao encontrada")
        if chat_session.player_id != player:
            abort(403, "Player nao autorizado para esta sessao")
        if not chat_session.is_active:
            abort(409, "Sessao encerrada")

        outgoing = Message(
            session_token=session_token,
            sender=Sender.PLAYER,
            content=message_text,
            created_at=sent_at,
        )
        db.add(outgoing)

    current_app.logger.info(
        "Mensagem do player registrada",
        extra={
            "event": "message.player.stored",
            "session_token": session_token,
            "player": player,
        },
    )

    start = monotonic()
    try:
        backend_response = dispatch_to_backend(session_token, player, message_text)
    except WebhookError as exc:
        current_app.logger.error(
            "Falha ao contatar backend",
            extra={
                "event": "backend.dispatch.failed",
                "session_token": session_token,
                "player": player,
                "error": str(exc),
            },
        )
        abort(502, str(exc))
    duration = monotonic() - start

    backend_message = backend_response.get("mensagem")
    if not isinstance(backend_message, str):
        current_app.logger.error(
            "Resposta invalida do backend",
            extra={
                "event": "backend.response.invalid",
                "session_token": session_token,
                "player": player,
                "payload": backend_response,
            },
        )
        abort(502, "Resposta invalida do backend")

    backend_message = backend_message.strip()
    received_at = datetime.now(timezone.utc)

    current_app.logger.info(
        "Resposta recebida do backend",
        extra={
            "event": "backend.response.received",
            "session_token": session_token,
            "player": player,
            "duration_ms": round(duration * 1000, 2),
        },
    )

    valezap_payload = {
        "sender": Sender.VALEZAP.value,
        "content": backend_message,
        "created_at": received_at.isoformat(),
    }

    ended = is_end_of_conversation(backend_message)

    with session_scope(session_identifier=session_token) as db:
        chat_session = _load_session(db, session_token)
        if chat_session is None:
            abort(404, "Sessao nao encontrada")
        if chat_session.player_id != player:
            abort(403, "Player nao autorizado para esta sessao")

        incoming = Message(
            session_token=session_token,
            sender=Sender.VALEZAP,
            content=backend_message,
            created_at=received_at,
        )
        db.add(incoming)

        if ended:
            chat_session.is_active = False
            chat_session.ended_at = received_at

    if ended:
        current_app.logger.info(
            "Sessao encerrada pelo backend",
            extra={
                "event": "session.ended",
                "session_token": session_token,
                "player": player,
            },
        )

    response_payload = {
        "player_message": player_payload,
        "valezap_message": valezap_payload,
        "ended": ended,
    }

    return jsonify(response_payload), 201



