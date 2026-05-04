"""
Unit tests for maskme.navigation
---------------------------------
Covers get_nested, set_nested, and delete_nested under normal,
edge-case, and malformed-input conditions.
"""

import pytest

from maskme.core._sentinel import _MISSING
from maskme.core.navigation import delete_nested, get_nested, set_nested


# ===========================================================================
# get_nested
# ===========================================================================


class TestGetNested:
    """Tests for the get_nested function."""

    # --- Happy path ---

    def test_flat_key_returns_value(self):
        """Single-segment path retrieves a top-level value."""
        assert get_nested({"email": "alice@example.com"}, "email") == "alice@example.com"

    def test_nested_two_levels(self):
        """Two-segment path traverses one level of nesting."""
        data = {"user": {"email": "alice@example.com"}}
        assert get_nested(data, "user.email") == "alice@example.com"

    def test_nested_three_levels(self):
        """Three-segment path traverses two levels of nesting."""
        data = {"a": {"b": {"c": 42}}}
        assert get_nested(data, "a.b.c") == 42

    def test_returns_none_when_value_is_explicitly_none(self):
        """An explicit None value is returned as-is, not confused with a missing key."""
        data = {"user": {"email": None}}
        result = get_nested(data, "user.email")
        assert result is None
        assert result is not _MISSING

    def test_returns_false_when_value_is_false(self):
        """Falsy values other than None are returned correctly."""
        assert get_nested({"active": False}, "active") is False

    def test_returns_zero_when_value_is_zero(self):
        """Zero is a valid value and must not be treated as missing."""
        assert get_nested({"count": 0}, "count") == 0

    def test_returns_empty_string(self):
        """An empty string is a valid value."""
        assert get_nested({"name": ""}, "name") == ""

    def test_returns_empty_list(self):
        """An empty list is a valid value."""
        assert get_nested({"tags": []}, "tags") == []

    # --- Missing paths → _MISSING ---

    def test_missing_top_level_key_returns_sentinel(self):
        """A key absent at the root returns _MISSING."""
        assert get_nested({}, "email") is _MISSING

    def test_missing_intermediate_key_returns_sentinel(self):
        """A missing intermediate node returns _MISSING."""
        data = {"user": {"name": "Alice"}}
        assert get_nested(data, "user.address.city") is _MISSING

    def test_missing_leaf_key_returns_sentinel(self):
        """An existing parent but absent leaf returns _MISSING."""
        data = {"user": {}}
        assert get_nested(data, "user.email") is _MISSING

    # --- Non-dict intermediates ---

    def test_intermediate_is_string_returns_sentinel(self):
        """If a non-dict value is encountered mid-path, return _MISSING."""
        data = {"user": "not_a_dict"}
        assert get_nested(data, "user.email") is _MISSING

    def test_intermediate_is_list_returns_sentinel(self):
        """Lists are not traversable by dot-notation; return _MISSING."""
        data = {"items": [{"id": 1}]}
        assert get_nested(data, "items.id") is _MISSING

    def test_intermediate_is_integer_returns_sentinel(self):
        """An integer intermediate node returns _MISSING."""
        data = {"user": 42}
        assert get_nested(data, "user.email") is _MISSING

    # --- Edge cases ---

    def test_empty_dict_returns_sentinel(self):
        """An empty source dict always returns _MISSING."""
        assert get_nested({}, "a.b.c") is _MISSING

    def test_deeply_nested_path(self):
        """A deeply nested path (5+ levels) is handled correctly."""
        data = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
        assert get_nested(data, "a.b.c.d.e") == "deep"

    def test_nested_value_is_a_dict(self):
        """The leaf value itself can be a dict."""
        inner = {"city": "Paris"}
        data = {"user": {"address": inner}}
        assert get_nested(data, "user.address") == inner


# ===========================================================================
# set_nested
# ===========================================================================


class TestSetNested:
    """Tests for the set_nested function."""

    # --- Happy path ---

    def test_flat_key_sets_value(self):
        """Single-segment path sets a top-level key."""
        data = {}
        set_nested(data, "email", "alice@example.com")
        assert data == {"email": "alice@example.com"}

    def test_nested_two_levels(self):
        """Two-segment path sets a value one level deep."""
        data = {}
        set_nested(data, "user.email", "alice@example.com")
        assert data == {"user": {"email": "alice@example.com"}}

    def test_nested_three_levels(self):
        """Three-segment path creates all intermediate dicts."""
        data = {}
        set_nested(data, "a.b.c", 99)
        assert data == {"a": {"b": {"c": 99}}}

    def test_overwrites_existing_value(self):
        """An existing value at the path is overwritten."""
        data = {"user": {"email": "old@example.com"}}
        set_nested(data, "user.email", "new@example.com")
        assert data["user"]["email"] == "new@example.com"

    def test_creates_missing_intermediate_nodes(self):
        """Missing intermediate dicts are created automatically."""
        data = {"user": {}}
        set_nested(data, "user.address.city", "Paris")
        assert data == {"user": {"address": {"city": "Paris"}}}

    def test_sets_none_value(self):
        """Explicitly setting None is supported."""
        data = {"user": {"email": "alice@example.com"}}
        set_nested(data, "user.email", None)
        assert data["user"]["email"] is None

    def test_sets_falsy_values(self):
        """Falsy values (False, 0, empty string) are set correctly."""
        data = {}
        set_nested(data, "active", False)
        set_nested(data, "count", 0)
        set_nested(data, "label", "")
        assert data == {"active": False, "count": 0, "label": ""}

    def test_sets_nested_dict_as_value(self):
        """A dict can be stored as a leaf value."""
        data = {}
        set_nested(data, "meta", {"version": 1})
        assert data == {"meta": {"version": 1}}

    def test_does_not_affect_sibling_keys(self):
        """Setting a value does not disturb sibling keys."""
        data = {"user": {"name": "Alice", "age": 30}}
        set_nested(data, "user.email", "alice@example.com")
        assert data["user"]["name"] == "Alice"
        assert data["user"]["age"] == 30

    def test_modifies_in_place(self):
        """set_nested modifies the original dict, not a copy."""
        data = {}
        original_id = id(data)
        set_nested(data, "key", "value")
        assert id(data) == original_id


# ===========================================================================
# delete_nested
# ===========================================================================


class TestDeleteNested:
    """Tests for the delete_nested function."""

    # --- Happy path ---

    def test_deletes_flat_key(self):
        """Single-segment path removes a top-level key."""
        data = {"email": "alice@example.com"}
        delete_nested(data, "email")
        assert "email" not in data

    def test_deletes_nested_key(self):
        """Two-segment path removes a nested key."""
        data = {"user": {"email": "alice@example.com", "age": 30}}
        delete_nested(data, "user.email")
        assert "email" not in data["user"]
        assert data["user"]["age"] == 30

    def test_deletes_deeply_nested_key(self):
        """A deep path is resolved correctly and the key is removed."""
        data = {"a": {"b": {"c": "secret"}}}
        delete_nested(data, "a.b.c")
        assert "c" not in data["a"]["b"]
        assert data == {"a": {"b": {}}}

    def test_leaves_parent_dict_intact(self):
        """The parent dict remains after removing its only child."""
        data = {"user": {"email": "alice@example.com"}}
        delete_nested(data, "user.email")
        assert "user" in data
        assert data["user"] == {}

    # --- No-op cases (must not raise) ---

    def test_missing_top_level_key_is_noop(self):
        """Deleting an absent top-level key silently does nothing."""
        data = {"name": "Alice"}
        delete_nested(data, "email")
        assert data == {"name": "Alice"}

    def test_missing_intermediate_node_is_noop(self):
        """Absent intermediate node causes a silent no-op (original bug)."""
        data = {"user": {"email": "alice@example.com"}}
        delete_nested(data, "user.phone.country_code")
        assert data == {"user": {"email": "alice@example.com"}}

    def test_missing_leaf_is_noop(self):
        """Existing parent but absent leaf: silent no-op, no KeyError."""
        data = {"user": {}}
        delete_nested(data, "user.email")
        assert data == {"user": {}}

    def test_empty_dict_is_noop(self):
        """Deleting from an empty dict is always a no-op."""
        data = {}
        delete_nested(data, "user.email")
        assert data == {}

    def test_non_dict_intermediate_is_noop(self):
        """If a path segment resolves to a non-dict, do nothing."""
        data = {"user": "not_a_dict"}
        delete_nested(data, "user.email")
        assert data == {"user": "not_a_dict"}

    def test_intermediate_is_list_is_noop(self):
        """A list intermediate causes a silent no-op."""
        data = {"items": [{"id": 1}]}
        delete_nested(data, "items.id")
        assert data == {"items": [{"id": 1}]}

    # --- Side-effect safety ---

    def test_does_not_affect_sibling_keys_at_root(self):
        """Deleting one root key does not affect others."""
        data = {"a": 1, "b": 2}
        delete_nested(data, "a")
        assert data == {"b": 2}

    def test_modifies_in_place(self):
        """delete_nested modifies the original dict (not a copy)."""
        data = {"email": "alice@example.com"}
        original_id = id(data)
        delete_nested(data, "email")
        assert id(data) == original_id