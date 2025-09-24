import pytest
from flask import Flask

from app.security import is_end_of_conversation, normalise_player, validate_message


def build_app(min_len=1, max_len=50):
    app = Flask(__name__)
    app.config["MIN_MESSAGE_LENGTH"] = min_len
    app.config["MAX_MESSAGE_LENGTH"] = max_len
    return app


def test_normalise_player_preserves_valid_identifier():
    assert normalise_player("Player_123") == "Player_123"


def test_normalise_player_sanitises_invalid_characters():
    assert normalise_player(" Player 123! ") == "Player-123-"


def test_validate_message_strips_and_validates_length():
    app = build_app()
    with app.app_context():
        assert validate_message("  olá  ") == "olá"


def test_validate_message_rejects_empty():
    app = build_app()
    with app.app_context():
        with pytest.raises(ValueError):
            validate_message("   ")


def test_validate_message_rejects_too_long():
    app = build_app(max_len=5)
    with app.app_context():
        with pytest.raises(ValueError):
            validate_message("abcdef")


def test_is_end_of_conversation_accepts_variants():
    assert is_end_of_conversation("fim da interação")
    assert is_end_of_conversation("Fim da Interacao")
    assert not is_end_of_conversation("continuar")
