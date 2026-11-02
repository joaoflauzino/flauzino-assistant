"""Pure utility helpers for text normalization in finance_api."""

import unicodedata


def strip_diacritics(text: str) -> str:
    """Removes diacritics while preserving the original casing and inner spacing."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def normalize_upper(text: str) -> str:
    """Normalizes text for accent- and case-insensitive matching in uppercase."""
    return strip_diacritics(text).upper().strip()


def normalize_lower(text: str) -> str:
    """Normalizes text for accent- and case-insensitive keys in lowercase."""
    return strip_diacritics(text).lower().strip()
