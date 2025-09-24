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
            "postgresql+psycopg://postgres:Mrs36861480!@evolution_postgres_python:5432/postgres_python",
        )
        REMOTE_WEBHOOK_URL: str = os.environ.get(
            "VALEZAP_BACKEND_URL",
            "https://n8n-n8n-webhook.jhbg9t.easypanel.host/webhook/34ae601d-ead7-491e-9bbc-f246089ee5e6",
        )
        REMOTE_WEBHOOK_TIMEOUT: float = float(os.environ.get("VALEZAP_BACKEND_TIMEOUT", "15"))
        REMOTE_WEBHOOK_API_KEY: str | None = os.environ.get("VALEZAP_BACKEND_API_KEY")
        WEBHOOK_API_KEY: str = os.environ.get("VALEZAP_WEBHOOK_API_KEY", "change-me")
        MAX_MESSAGE_LENGTH: int = str_to_int(os.environ.get("VALEZAP_MAX_MESSAGE_LENGTH"), 700)
        MIN_MESSAGE_LENGTH: int = 1
        SESSION_TTL: timedelta = timedelta(hours=str_to_int(os.environ.get("VALEZAP_SESSION_HOURS"), 2))
        LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
        ALLOWED_ORIGINS: tuple[str, ...] = tuple(
            origin.strip()
            for origin in os.environ.get("VALEZAP_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )

    return Config
