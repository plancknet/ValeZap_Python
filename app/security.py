from __future__ import annotations

import re
import unicodedata
from uuid import uuid4

from flask import current_app

E164_PATTERN = re.compile(r"^[1-9]\d{7,14}$")
PLAYER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def normalise_player(raw_player: str | None) -> str | None:
    if not raw_player:
        return None

    normalised = unicodedata.normalize("NFKC", raw_player).strip()
    if not normalised:
        return None

    digits_only = re.sub(r"\D", "", normalised)
    if digits_only:
        if E164_PATTERN.fullmatch(digits_only):
            return digits_only
        if not re.search(r"\D", normalised):
            return None

    if PLAYER_ID_PATTERN.fullmatch(normalised):
        return normalised

    safe = re.sub(r"[^A-Za-z0-9_-]", "-", normalised).strip("-")
    return safe[:64] or None


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


def generate_player_identifier(country_code: str = "55") -> str:
    digits_cc = re.sub(r"\D", "", country_code or "")
    digits_cc = digits_cc.lstrip("0") or "55"

    remaining = max(8 - len(digits_cc), 0)
    target_total = min(max(len(digits_cc) + max(remaining, 10), 8), 15)
    random_span = max(target_total - len(digits_cc), 1)

    random_value = f"{uuid4().int % (10 ** random_span):0{random_span}d}"
    candidate = f"{digits_cc}{random_value}"[:15]

    if not E164_PATTERN.fullmatch(candidate):
        return "551100000000"

    return candidate
