from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def str_to_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_config() -> type:
    """Return the default configuration class for the application."""

    @dataclass
    class Config:
        SECRET_KEY: str = os.environ.get("SECRET_KEY", "valezap-dev-secret")
        DATABASE_URL: str = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/valezap",
        )
        REMOTE_WEBHOOK_URL: str = os.environ.get(
            "VALEZAP_BACKEND_URL",
            "https://quizzgpt-n8n.jhbg9t.easypanel.host/webhook/11648d55-4d9c-4015-a1f6-b9b173cd1765",
        )
        REMOTE_WEBHOOK_TIMEOUT: float = float(os.environ.get("VALEZAP_BACKEND_TIMEOUT", "15"))
        REMOTE_WEBHOOK_API_KEY: str | None = os.environ.get("VALEZAP_BACKEND_API_KEY")
        WEBHOOK_API_KEY: str = os.environ.get("VALEZAP_WEBHOOK_API_KEY", "change-me")
        MAX_MESSAGE_LENGTH: int = str_to_int(os.environ.get("VALEZAP_MAX_MESSAGE_LENGTH"), 700)
        MIN_MESSAGE_LENGTH: int = 1
        SESSION_TTL: timedelta = timedelta(hours=str_to_int(os.environ.get("VALEZAP_SESSION_HOURS"), 2))
        ALLOWED_ORIGINS: tuple[str, ...] = tuple(
            origin.strip()
            for origin in os.environ.get("VALEZAP_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )

    return Config
