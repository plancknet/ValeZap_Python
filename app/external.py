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

    try:
        response = requests.post(url, json=payload, timeout=timeout, headers=headers)
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise WebhookError("Não foi possível contatar o backend do ValeZap") from exc

    if not response.ok:
        raise WebhookError(f"Backend retornou status inesperado: {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise WebhookError("Resposta do backend não está em JSON válido") from exc

    if not isinstance(data, dict):
        raise WebhookError("Formato de resposta inválido do backend")

    return data
