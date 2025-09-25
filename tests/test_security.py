import pytest
from flask import Flask

from app.security import (
    generate_player_identifier,
    is_end_of_conversation,
    normalise_player,
    validate_message,
)


def build_app(min_len=1, max_len=50):
    app = Flask(__name__)
    app.config["MIN_MESSAGE_LENGTH"] = min_len
    app.config["MAX_MESSAGE_LENGTH"] = max_len
    return app


def test_normalise_player_preserves_valid_identifier():
    assert normalise_player("Player_123") == "Player_123"


def test_normalise_player_accepts_e164():
    assert normalise_player("+55 (12) 99197-4241") == "5512991974241"


def test_normalise_player_rejects_invalid_phone():
    assert normalise_player("00123") is None


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


def test_generate_player_identifier_produces_valid_digits():
    for _ in range(5):
        identifier = generate_player_identifier()
        assert identifier.isdigit()
        assert 8 <= len(identifier) <= 15
        assert identifier[0] != "0"


def test_is_end_of_conversation_accepts_variants():
    assert is_end_of_conversation("fim da interação")
    assert is_end_of_conversation("Fim da Interacao")
    assert not is_end_of_conversation("continuar")
