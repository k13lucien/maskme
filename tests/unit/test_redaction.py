"""
Unit tests for maskme.strategies.redaction
--------------------------------------------
Covers validators, core redaction logic, edge cases, and documents
the current behaviour of None and overlapping keep windows.
"""

from typing import Any

import pytest

from maskme.strategies.redaction import _validate_char, _validate_keep, apply


# ===========================================================================
# _validate_char
# ===========================================================================


class TestValidateChar:

    def test_single_char_is_valid(self):
        _validate_char("*")

    def test_any_single_char_is_valid(self):
        for c in ["#", "X", " ", "-", "0"]:
            _validate_char(c)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="single character"):
            _validate_char("")

    def test_two_chars_raises(self):
        with pytest.raises(ValueError, match="single character"):
            _validate_char("**")

    def test_long_string_raises(self):
        with pytest.raises(ValueError, match="single character"):
            _validate_char("redacted")


# ===========================================================================
# _validate_keep
# ===========================================================================


class TestValidateKeep:

    def test_both_zero_is_valid(self):
        _validate_keep(0, 0)

    def test_positive_integers_are_valid(self):
        _validate_keep(3, 4)

    def test_keep_start_negative_raises(self):
        with pytest.raises(ValueError, match="keep_start"):
            _validate_keep(-1, 0)

    def test_keep_end_negative_raises(self):
        with pytest.raises(ValueError, match="keep_end"):
            _validate_keep(0, -1)

    def test_keep_start_float_raises(self):
        with pytest.raises(ValueError, match="keep_start"):
            _validate_keep(1.5, 0)

    def test_keep_end_float_raises(self):
        with pytest.raises(ValueError, match="keep_end"):
            _validate_keep(0, 2.0)

    def test_keep_start_string_raises(self):
        with pytest.raises(ValueError, match="keep_start"):
            _validate_keep("3", 0)


# ===========================================================================
# apply() — core redaction logic
# ===========================================================================


class TestApplyCore:

    def test_full_redaction_by_default(self):
        """With no keep windows, the entire value is redacted."""
        assert apply("alice@example.com") == "*" * len("alice@example.com")

    def test_output_length_equals_input_length(self):
        """Redacted string always has the same length as the original."""
        value = "alice@example.com"
        assert len(apply(value)) == len(value)

    def test_keep_start_only(self):
        """Only the first N characters are visible."""
        assert apply("alice@example.com", keep_start=5) == "alice************"

    def test_keep_end_only(self):
        """Only the last N characters are visible."""
        assert apply("4111111111111234", char="#", keep_end=4) == "############1234"

    def test_keep_start_and_end(self):
        """Both ends are visible, middle is redacted."""
        assert apply("alice@example.com", keep_start=5, keep_end=4) == "alice********" + ".com"

    def test_keep_start_and_end_correct(self):
        value = "1234567890"
        result = apply(value, keep_start=2, keep_end=2)
        assert result == "12******90"

    def test_custom_char(self):
        """Custom redaction character is applied correctly."""
        assert apply("secret", char="#") == "######"

    def test_custom_char_with_keep(self):
        assert apply("secret", char="-", keep_start=2, keep_end=2) == "se--et"

    def test_output_is_always_string(self):
        """Return type is always str."""
        assert isinstance(apply("hello"), str)
        assert isinstance(apply(42), str)
        assert isinstance(apply(None), str)


# ===========================================================================
# apply() — length preservation
# ===========================================================================


class TestLengthPreservation:

    @pytest.mark.parametrize("value,keep_start,keep_end", [
        ("hello", 0, 0),
        ("hello", 2, 0),
        ("hello", 0, 2),
        ("hello", 2, 2),
        ("hello", 5, 0),
        ("hello", 0, 5),
        ("a", 0, 0),
        ("", 0, 0),
    ])
    def test_length_always_preserved(self, value, keep_start, keep_end):
        """Output length always equals len(str(value)) regardless of keep windows."""
        result = apply(value, keep_start=keep_start, keep_end=keep_end)
        assert len(result) == len(str(value))


# ===========================================================================
# apply() — overlapping keep windows
# ===========================================================================


class TestOverlappingWindows:

    def test_keep_sum_equals_length_redacts_all(self):
        """keep_start + keep_end == length → full redaction (documented behaviour)."""
        value = "hello"
        result = apply(value, keep_start=3, keep_end=2)
        assert result == "*" * len(value)

    def test_keep_sum_exceeds_length_redacts_all(self):
        """keep_start + keep_end > length → full redaction, no error."""
        value = "hi"
        result = apply(value, keep_start=10, keep_end=10)
        assert result == "*" * len(value)

    def test_large_keep_start_on_short_string(self):
        """keep_start larger than string → full redaction."""
        result = apply("abc", keep_start=1_000)
        assert result == "***"


# ===========================================================================
# apply() — input type handling
# ===========================================================================


class TestInputTypes:

    def test_integer_input(self):
        """Integers are converted to string before redaction."""
        result = apply(123456, keep_start=2, keep_end=2)
        assert result == "12**56"

    def test_float_input(self):
        result = apply(3.14159, keep_start=1)
        assert result[0] == "3"
        assert len(result) == len(str(3.14159))

    def test_boolean_true(self):
        """True is converted to 'True' (4 chars)."""
        result = apply(True, keep_start=1)
        assert result == "T***"

    def test_boolean_false(self):
        result = apply(False, keep_start=1)
        assert result == "F****"

    def test_none_is_converted_to_string(self):
        """None becomes 'None' (4 chars) — documents current behaviour.
        Callers that want to skip None should handle it upstream via the engine."""
        result = apply(None)
        assert result == ""
        assert len(result) == 0

    def test_empty_string(self):
        """An empty string produces an empty redacted string."""
        assert apply("") == ""


# ===========================================================================
# apply() — validation errors
# ===========================================================================


class TestApplyValidation:

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError, match="single character"):
            apply("hello", char="##")

    def test_empty_char_raises(self):
        with pytest.raises(ValueError, match="single character"):
            apply("hello", char="")

    def test_negative_keep_start_raises(self):
        with pytest.raises(ValueError, match="keep_start"):
            apply("hello", keep_start=-1)

    def test_negative_keep_end_raises(self):
        with pytest.raises(ValueError, match="keep_end"):
            apply("hello", keep_end=-1)


# ===========================================================================
# apply() — kwargs forwarding
# ===========================================================================


class TestKwargsAccepted:

    def test_accepts_salt_and_extra_kwargs(self):
        """Extra kwargs forwarded by the engine are accepted without raising."""
        result = apply("hello", char="*", keep_start=1, salt="secret", foo="bar")
        assert result == "h****"