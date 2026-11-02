"""Unit tests for the shared text normalization helpers."""

import pytest

from finance_api.core.text import normalize_lower, normalize_upper, strip_diacritics


def test_strip_diacritics_keeps_the_original_casing():
    assert strip_diacritics("São Paulo - Ação") == "Sao Paulo - Acao"


def test_strip_diacritics_keeps_text_without_accents_untouched():
    assert strip_diacritics("C6 JOÃO 123") == "C6 JOAO 123"


def test_normalize_upper_removes_diacritics_trims_and_uppercases():
    assert normalize_upper("  São Paulo - Ação  ") == "SAO PAULO - ACAO"


def test_normalize_lower_removes_diacritics_trims_and_lowercases():
    assert normalize_lower("  Premiação  ") == "premiacao"


def test_normalize_lower_matches_accented_display_name_to_plain_key():
    """The unmatched-key fallback in the repositories relies on this equality."""
    assert normalize_lower("Premiação") == normalize_lower("premiacao")


def test_normalize_upper_and_lower_are_idempotent():
    once = normalize_upper("Salário")
    assert normalize_upper(once) == once

    once_lower = normalize_lower("Salário")
    assert normalize_lower(once_lower) == once_lower


@pytest.mark.parametrize("value", ["", "   "])
def test_normalizers_collapse_blank_input(value: str):
    assert normalize_upper(value) == ""
    assert normalize_lower(value) == ""
