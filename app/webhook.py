from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, jsonify, request
from sqlalchemy import select

from .database import session_scope
from .models import ChatSession, Message, Sender
from .security import is_end_of_conversation, normalise_player

webhook_bp = Blueprint("webhook", __name__)


def _load_session(db, session_token: str) -> ChatSession | None:
    stmt = select(ChatSession).where(ChatSession.session_token == session_token)
    return db.execute(stmt).scalar_one_or_none()


@webhook_bp.post("/vale")
def receive_backend_message():
    expected_api_key = current_app.config["WEBHOOK_API_KEY"]
    provided_api_key = request.headers.get("X-API-Key")
    if expected_api_key and provided_api_key != expected_api_key:
        current_app.logger.warning(
            "Webhook rejeitado por API key invalida",
            extra={
                "event": "webhook.rejected",
                "reason": "invalid_api_key",
            },
        )
        abort(401, "API key invalida")

    payload = request.get_json(silent=True) or {}

    session_token = payload.get("sessao")
    player = normalise_player(payload.get("player"))
    raw_message = payload.get("mensagem")

    if not session_token:
        abort(400, "sessao obrigatoria")
    if not player:
        abort(400, "player invalido")
    if not isinstance(raw_message, str):
        abort(400, "mensagem invalida")

    message_text = raw_message.strip()
    if not message_text:
        abort(400, "mensagem vazia")

    with session_scope(session_identifier=session_token) as db:
        chat_session = _load_session(db, session_token)
        if chat_session is None:
            abort(404, "Sessao nao encontrada")
        if chat_session.player_id != player:
            abort(403, "Sessao nao pertence ao player informado")

        received_at = datetime.now(timezone.utc)
        incoming = Message(
            session_token=session_token,
            sender=Sender.VALEZAP,
            content=message_text,
            created_at=received_at,
        )
        db.add(incoming)

        ended = is_end_of_conversation(message_text)
        if ended:
            chat_session.is_active = False
            chat_session.ended_at = received_at

    current_app.logger.info(
        "Mensagem recebida via webhook",
        extra={
            "event": "webhook.message.received",
            "session_token": session_token,
            "player": player,
            "ended": ended,
        },
    )

    return jsonify({"status": "ok", "ended": ended}), 200
