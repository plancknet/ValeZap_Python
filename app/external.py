from __future__ import annotations

from typing import Any

import requests
from flask import current_app


class WebhookError(RuntimeError):
    """Raised when the remote ValeZap backend cannot be reached."""


def dispatch_to_backend(session_token: str, player_id: str, message: str) -> dict[str, Any]:
    """Send the player message to the upstream workflow and return its JSON response."""
    url = current_app.config["REMOTE_WEBHOOK_URL"]
    timeout = current_app.config["REMOTE_WEBHOOK_TIMEOUT"]
    api_key = current_app.config.get("REMOTE_WEBHOOK_API_KEY")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    payload = {
        "sessao": session_token,
        "player": player_id,
        "mensagem": message,
    }

    logger = current_app.logger
    logger.debug(
        "Enviando mensagem ao backend",
        extra={
            "event": "backend.dispatch",
            "session_token": session_token,
            "player": player_id,
            "url": url,
        },
    )

    try:
        response = requests.post(url, json=payload, timeout=timeout, headers=headers)
    except requests.RequestException as exc:  # pragma: no cover - network failure
        logger.error(
            "Nao foi possivel contatar o backend",
            extra={
                "event": "backend.dispatch.error",
                "session_token": session_token,
                "player": player_id,
                "error": str(exc),
            },
        )
        raise WebhookError("Não foi possível contatar o backend do ValeZap") from exc

    if not response.ok:
        logger.error(
            "Backend retornou status inesperado",
            extra={
                "event": "backend.dispatch.status",
                "session_token": session_token,
                "player": player_id,
                "status_code": response.status_code,
                "body": response.text[:500],
            },
        )
        raise WebhookError(f"Backend retornou status inesperado: {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        logger.error(
            "Resposta do backend nao esta em JSON valido",
            extra={
                "event": "backend.dispatch.invalid_json",
                "session_token": session_token,
                "player": player_id,
                "body": response.text[:500],
            },
        )
        raise WebhookError("Resposta do backend não está em JSON válido") from exc

    if not isinstance(data, dict):
        logger.error(
            "Formato de resposta invalido do backend",
            extra={
                "event": "backend.dispatch.invalid_payload",
                "session_token": session_token,
                "player": player_id,
                "payload": data,
            },
        )
        raise WebhookError("Formato de resposta inválido do backend")

    return data
