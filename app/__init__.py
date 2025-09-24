from __future__ import annotations

import logging
from logging import Logger

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .config import load_config
from .database import init_engine
from .api import api_bp
from .routes import ui_bp
from .webhook import webhook_bp


def create_app(config_object: type | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    config_cls = config_object or load_config()
    app.config.from_object(config_cls)

    _configure_logging(app)
    init_engine(app)

    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(webhook_bp, url_prefix="/webhook")

    _register_error_handlers(app)
    _register_response_headers(app)

    return app


def _configure_logging(app: Flask) -> None:
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logger: Logger = app.logger
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.debug("Logging configured", extra={"component": "bootstrap"})


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        if request.accept_mimetypes.best == "application/json" or request.path.startswith("/api"):
            response = {"error": exc.name, "message": exc.description}
            return jsonify(response), exc.code
        return exc


def _register_response_headers(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):  # pragma: no cover - header mutation only
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
        )
        return response
