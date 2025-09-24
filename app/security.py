from __future__ import annotations

import re
import unicodedata

from flask import current_app

PLAYER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def normalise_player(raw_player: str | None) -> str | None:
    if not raw_player:
        return None
    normalised = unicodedata.normalize("NFKC", raw_player).strip()
    if not normalised:
        return None
    if PLAYER_ID_PATTERN.fullmatch(normalised):
        return normalised
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", normalised)
    return safe[:64]


def validate_message(content: str) -> str:
    if content is None:
        raise ValueError("Mensagem obrigatória")

    clean = unicodedata.normalize("NFKC", content).strip()
    min_len = current_app.config.get("MIN_MESSAGE_LENGTH", 1)
    max_len = current_app.config.get("MAX_MESSAGE_LENGTH", 700)

    if len(clean) < min_len:
        raise ValueError("Mensagem muito curta")
    if len(clean) > max_len:
        raise ValueError("Mensagem muito longa")

    if any(ord(char) < 32 and char not in ("\n", "\r", "\t") for char in clean):
        raise ValueError("Mensagem contém caracteres inválidos")

    return clean

def is_end_of_conversation(message: str) -> bool:
    if not message:
        return False
    normalised = unicodedata.normalize("NFKC", message).strip()
    if not normalised:
        return False
    folded = normalised.casefold()
    ascii_folded = unicodedata.normalize("NFKD", normalised).encode("ascii", "ignore").decode("ascii").casefold()
    return folded == "fim da interação" or ascii_folded == "fim da interacao"
