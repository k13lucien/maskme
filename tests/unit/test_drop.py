"""
Unit tests for maskme.strategies.drop
--------------------------------------
The drop strategy has a single responsibility: return DROP_SENTINEL
regardless of the input value. Tests cover all input types and verify
that the returned value is always the shared constant, never a raw string.
"""

from typing import Any

import pytest

from maskme.strategies.base import DROP_SENTINEL
from maskme.strategies.drop import apply


# ---------------------------------------------------------------------------
# Return value contract
# ---------------------------------------------------------------------------


class TestReturnValue:
    """The return value must always be DROP_SENTINEL, for any input."""

    def test_returns_drop_sentinel_constant(self):
        """Return value is identical to DROP_SENTINEL (not just equal)."""
        assert apply("anything") is DROP_SENTINEL

    def test_returns_string(self):
        """Return type is always str."""
        assert isinstance(apply("x"), str)

    def test_not_a_hardcoded_string(self):
        """Return value equals DROP_SENTINEL — guards against sentinel drift."""
        assert apply("x") == DROP_SENTINEL


# ---------------------------------------------------------------------------
# Input indifference — value is always ignored
# ---------------------------------------------------------------------------


class TestInputIndifference:
    """apply() must return DROP_SENTINEL regardless of what value is passed."""

    @pytest.mark.parametrize("value", [
        "alice@example.com",
        123,
        3.14,
        True,
        False,
        [],
        {},
        None,
        "",
        0,
    ])
    def test_always_drops_any_value(self, value: Any):
        """DROP_SENTINEL is returned for every possible input type."""
        assert apply(value) == DROP_SENTINEL


# ---------------------------------------------------------------------------
# Keyword arguments are accepted and ignored
# ---------------------------------------------------------------------------


class TestKwargsAccepted:
    """Extra kwargs must be accepted without raising — engine may pass salt and params."""

    def test_accepts_salt_kwarg(self):
        """salt kwarg forwarded by the engine is silently ignored."""
        assert apply("value", salt="my-secret") == DROP_SENTINEL

    def test_accepts_arbitrary_kwargs(self):
        """Any extra keyword arguments are accepted without error."""
        assert apply("value", salt="s", foo="bar", depth=2) == DROP_SENTINEL