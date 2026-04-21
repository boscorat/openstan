"""
test_safe_hex_id.py — unit tests for the _safe_hex_id validation helper.

``_safe_hex_id`` is a security guard used across multiple models to prevent
raw interpolation of untrusted strings into ``setFilter`` SQL expressions.
These tests pin its boundary conditions and error behaviour.

No Qt or database fixtures required — pure Python.
"""

import pytest

from openstan.models.statement_queue_model import _safe_hex_id


class TestSafeHexId:
    """Tests for _safe_hex_id validation logic."""

    # ── Happy path ────────────────────────────────────────────────────────

    def test_valid_32_char_hex_returns_value(self) -> None:
        """A valid 32-char lowercase hex string is returned unchanged."""
        value = "a" * 32
        assert _safe_hex_id(value) == value

    def test_valid_hex_with_all_chars(self) -> None:
        """All valid hex digits (0-9, a-f) are accepted."""
        value = "0123456789abcdef" * 2  # 32 chars
        assert _safe_hex_id(value) == value

    def test_returns_same_object(self) -> None:
        """The return value is the same string object passed in."""
        value = "deadbeef" * 4  # 32 chars
        result = _safe_hex_id(value)
        assert result is value

    # ── Length boundary violations ────────────────────────────────────────

    def test_31_chars_raises_value_error(self) -> None:
        """One character too short raises ValueError."""
        with pytest.raises(ValueError):
            _safe_hex_id("a" * 31)

    def test_33_chars_raises_value_error(self) -> None:
        """One character too long raises ValueError."""
        with pytest.raises(ValueError):
            _safe_hex_id("a" * 33)

    def test_empty_string_raises_value_error(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError):
            _safe_hex_id("")

    def test_zero_chars_is_not_32(self) -> None:
        """Sanity: empty string is length 0, not 32."""
        with pytest.raises(ValueError, match="32-char hex"):
            _safe_hex_id("")

    # ── Character set violations ──────────────────────────────────────────

    def test_uppercase_hex_raises_value_error(self) -> None:
        """Uppercase hex chars (A-F) are rejected — must be lowercase."""
        value = "A" * 32
        with pytest.raises(ValueError):
            _safe_hex_id(value)

    def test_uuid_with_hyphens_raises_value_error(self) -> None:
        """A standard UUID string (with hyphens) is rejected.

        This is the most common mistake callers could make — passing a
        ``str(uuid4())`` instead of ``uuid4().hex``.
        """
        uuid_with_hyphens = "550e8400-e29b-41d4-a716-446655440000"  # 36 chars, hyphens
        with pytest.raises(ValueError):
            _safe_hex_id(uuid_with_hyphens)

    def test_non_hex_chars_raise_value_error(self) -> None:
        """Non-hex characters (g-z, spaces, punctuation) are rejected."""
        value = "g" * 32
        with pytest.raises(ValueError):
            _safe_hex_id(value)

    def test_space_in_value_raises_value_error(self) -> None:
        """Spaces are not valid hex chars and must be rejected."""
        value = ("a" * 31) + " "
        with pytest.raises(ValueError):
            _safe_hex_id(value)

    def test_sql_injection_attempt_raises_value_error(self) -> None:
        """A SQL injection string is rejected (the whole point of this guard)."""
        value = "' OR '1'='1" + "a" * 20  # not 32 valid hex chars
        with pytest.raises(ValueError):
            _safe_hex_id(value)

    # ── Error message quality ──────────────────────────────────────────────

    def test_error_message_contains_invalid_value(self) -> None:
        """The ValueError message includes the offending value for debuggability."""
        bad = "not_valid_at_all_xx"
        with pytest.raises(ValueError, match="not_valid_at_all_xx"):
            _safe_hex_id(bad)

    def test_error_message_mentions_32_char(self) -> None:
        """The error message mentions the expected 32-char hex format."""
        with pytest.raises(ValueError, match="32-char hex"):
            _safe_hex_id("tooshort")
