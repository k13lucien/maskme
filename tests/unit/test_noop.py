"""
Unit tests for maskme.strategies.noop
---------------------------------------
The noop strategy has one invariant: the return value must always be
identical (same object) to the input value, for any type whatsoever.
"""

from typing import Any

import pytest

from maskme.strategies.noop import apply


# ===========================================================================
# Identity contract — return value must be the exact same object
# ===========================================================================


class TestIdentity:

    @pytest.mark.parametrize("value", [
        "alice@example.com",
        "",
        "0",
        123,
        0,
        -1,
        3.14,
        0.0,
        True,
        False,
        None,
        [],
        [1, 2, 3],
        {},
        {"key": "value"},
        (1, 2),
        {1, 2, 3},
    ])
    def test_returns_same_object(self, value: Any):
        """Return value is identical (is) to the input — no copy, no transformation."""
        assert apply(value) is value


# ===========================================================================
# Return type matches input type
# ===========================================================================


class TestReturnType:

    def test_string_returns_string(self):
        assert isinstance(apply("hello"), str)

    def test_int_returns_int(self):
        assert isinstance(apply(42), int)

    def test_float_returns_float(self):
        assert isinstance(apply(3.14), float)

    def test_none_returns_none(self):
        assert apply(None) is None

    def test_list_returns_list(self):
        assert isinstance(apply([1, 2]), list)

    def test_dict_returns_dict(self):
        assert isinstance(apply({"a": 1}), dict)


# ===========================================================================
# kwargs are accepted and ignored
# ===========================================================================


class TestKwargsAccepted:

    def test_accepts_salt_kwarg(self):
        """salt forwarded by the engine is silently ignored."""
        assert apply("value", salt="secret") == "value"

    def test_accepts_arbitrary_kwargs(self):
        assert apply(42, salt="s", foo="bar", depth=2) == 42