"""Pure utility helpers for text normalization in finance_api."""

import unicodedata


def normalize_text(text: str) -> str:
    """Normalizes text by removing diacritics and converting to uppercase."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


# Alias backward-compatible
_normalize = normalize_text
