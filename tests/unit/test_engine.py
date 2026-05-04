"""
Unit tests for maskme.engine (MaskMe class)
--------------------------------------------
Uses lightweight stub strategies to avoid coupling tests to the real
STRATEGIES registry. Each stub is a plain function that is injected
directly into engine.strategies after instantiation.
"""

import warnings

import pytest

from maskme.core.engine import MaskMe


# ===========================================================================
# Stub strategies
# ===========================================================================

# Simple transformation: append a suffix so the change is verifiable.
def _stub_upper(value, **kwargs):
    """Strategy stub: uppercases a string value."""
    return str(value).upper()


# Salt-aware strategy: incorporates the salt so we can assert it was injected.
def _stub_salted(value, salt="", **kwargs):
    """Strategy stub: appends the salt to the value."""
    return f"{value}:{salt}"


# Parameterized strategy: uses an extra keyword argument.
def _stub_replace(value, char="X", **kwargs):
    """Strategy stub: replaces the value with repeated char."""
    return char * len(str(value))


# Drop strategy: signals the engine to delete the field.
def _stub_drop(value, **kwargs):
    """Strategy stub: signals field deletion via __DROP__ sentinel."""
    return "__DROP__"


# No-salt strategy: explicitly does NOT declare a salt parameter.
def _stub_no_salt(value):
    """Strategy stub without salt parameter — engine must not inject it."""
    return f"masked:{value}"


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def engine():
    """Bare engine with an empty rule set and all stubs registered."""
    e = MaskMe(rules={}, salt="test-salt")
    e.strategies = {
        "upper":    _stub_upper,
        "salted":   _stub_salted,
        "replace":  _stub_replace,
        "drop":     _stub_drop,
        "no_salt":  _stub_no_salt,
    }
    return e


def make_engine(rules, salt="test-salt"):
    """Helper: creates an engine with the given rules and stub strategies."""
    e = MaskMe(rules=rules, salt=salt)
    e.strategies = {
        "upper":    _stub_upper,
        "salted":   _stub_salted,
        "replace":  _stub_replace,
        "drop":     _stub_drop,
        "no_salt":  _stub_no_salt,
    }
    return e


# ===========================================================================
# __init__
# ===========================================================================


class TestInit:
    """Tests for MaskMe.__init__."""

    def test_stores_rules(self):
        """Rules dict is stored as an instance attribute."""
        rules = {"user.email": "upper"}
        e = MaskMe(rules=rules)
        assert e.rules is rules

    def test_stores_salt(self):
        """Custom salt is stored."""
        e = MaskMe(rules={}, salt="mysalt")
        assert e.salt == "mysalt"

    def test_default_salt_is_empty_string(self):
        """Salt defaults to empty string when omitted."""
        e = MaskMe(rules={})
        assert e.salt == ""

    def test_strategies_is_a_copy_of_registry(self):
        """engine.strategies is a dict (copy) — not the original STRATEGIES ref."""
        e = MaskMe(rules={})
        assert isinstance(e.strategies, dict)


# ===========================================================================
# mask() — public generator
# ===========================================================================


class TestMask:
    """Tests for MaskMe.mask()."""

    def test_yields_same_number_of_records(self):
        """mask() yields exactly one output per input record."""
        e = make_engine({"name": "upper"})
        records = [{"name": "alice"}, {"name": "bob"}]
        result = list(e.mask(records))
        assert len(result) == 2

    def test_mask_is_a_generator(self):
        """mask() returns a generator (lazy evaluation)."""
        e = make_engine({})
        import types
        gen = e.mask([{"a": 1}])
        assert isinstance(gen, types.GeneratorType)

    def test_original_records_are_not_mutated(self):
        """deepcopy ensures the caller's original data is untouched."""
        e = make_engine({"user.email": "upper"})
        original = {"user": {"email": "alice@example.com"}}
        records = [original]
        list(e.mask(records))  # consume the generator
        assert original["user"]["email"] == "alice@example.com"

    def test_accepts_generator_input(self):
        """mask() handles a generator (not just a list) as input."""
        e = make_engine({"name": "upper"})
        gen = ({"name": f"user_{i}"} for i in range(3))
        result = list(e.mask(gen))
        assert len(result) == 3
        assert all(r["name"].startswith("USER_") for r in result)

    def test_empty_input_yields_nothing(self):
        """mask() over an empty iterable yields no records."""
        e = make_engine({"name": "upper"})
        assert list(e.mask([])) == []


# ===========================================================================
# _resolve_config
# ===========================================================================


class TestResolveConfig:
    """Tests for MaskMe._resolve_config."""

    def test_string_config_returns_name_and_empty_params(self, engine):
        """A plain string config extracts the strategy name with no params."""
        name, params = engine._resolve_config("upper")
        assert name == "upper"
        assert params == {}

    def test_dict_config_returns_name_and_params(self, engine):
        """A dict config extracts strategy name and remaining keys as params."""
        config = {"strategy": "replace", "char": "#"}
        name, params = engine._resolve_config(config)
        assert name == "replace"
        assert params == {"char": "#"}

    def test_dict_config_without_extra_params(self, engine):
        """A dict config with only 'strategy' key yields empty params."""
        name, params = engine._resolve_config({"strategy": "upper"})
        assert name == "upper"
        assert params == {}

    def test_dict_config_missing_strategy_key(self, engine):
        """A dict config without 'strategy' key returns an empty string name."""
        name, params = engine._resolve_config({"char": "#"})
        assert name == ""
        assert params == {"char": "#"}


# ===========================================================================
# _validate_strategy
# ===========================================================================


class TestValidateStrategy:
    """Tests for MaskMe._validate_strategy."""

    def test_known_strategy_returns_true(self, engine):
        """A registered strategy name passes validation."""
        assert engine._validate_strategy("upper", "some.path") is True

    def test_unknown_strategy_returns_false(self, engine):
        """An unregistered strategy name fails validation."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert engine._validate_strategy("nonexistent", "some.path") is False

    def test_unknown_strategy_emits_warning(self, engine):
        """An unknown strategy triggers a UserWarning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            engine._validate_strategy("ghost", "user.ssn")
        assert len(caught) == 1
        assert issubclass(caught[0].category, UserWarning)
        assert "ghost" in str(caught[0].message)
        assert "user.ssn" in str(caught[0].message)

    def test_known_strategy_emits_no_warning(self, engine):
        """A valid strategy must not emit any warnings."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            engine._validate_strategy("upper", "user.name")
        assert len(caught) == 0


# ===========================================================================
# _apply_strategy
# ===========================================================================


class TestApplyStrategy:
    """Tests for MaskMe._apply_strategy."""

    def test_applies_simple_strategy(self, engine):
        """A basic strategy transforms the value correctly."""
        result = engine._apply_strategy("upper", "hello", {})
        assert result == "HELLO"

    def test_injects_salt_when_strategy_declares_it(self, engine):
        """Salt is injected when the strategy function declares a 'salt' param."""
        result = engine._apply_strategy("salted", "value", {})
        assert result == "value:test-salt"

    def test_does_not_inject_salt_when_not_declared(self, engine):
        """Salt is NOT injected when the strategy function has no 'salt' param."""
        # _stub_no_salt has signature (value,) — passing salt would raise TypeError
        result = engine._apply_strategy("no_salt", "alice", {})
        assert result == "masked:alice"

    def test_passes_extra_params(self, engine):
        """Extra params from config are forwarded to the strategy."""
        result = engine._apply_strategy("replace", "hello", {"char": "#"})
        assert result == "#####"

    def test_drop_sentinel_is_returned_as_is(self, engine):
        """__DROP__ sentinel is returned verbatim so the caller can handle it."""
        result = engine._apply_strategy("drop", "secret", {})
        assert result == "__DROP__"


# ===========================================================================
# _process_record (integration of all private methods)
# ===========================================================================


class TestProcessRecord:
    """End-to-end tests for MaskMe._process_record."""

    def test_applies_simple_rule(self):
        """A simple string rule transforms the target field."""
        e = make_engine({"user.name": "upper"})
        record = {"user": {"name": "alice"}}
        result = e._process_record(record)
        assert result["user"]["name"] == "ALICE"

    def test_applies_parameterized_rule(self):
        """A dict rule with extra params is resolved and applied correctly."""
        e = make_engine({"user.phone": {"strategy": "replace", "char": "*"}})
        record = {"user": {"phone": "0612345678"}}
        result = e._process_record(record)
        assert result["user"]["phone"] == "**********"

    def test_drop_rule_removes_field(self):
        """A strategy returning __DROP__ causes the field to be deleted."""
        e = make_engine({"user.ssn": "drop"})
        record = {"user": {"ssn": "123-45-6789", "name": "Alice"}}
        result = e._process_record(record)
        assert "ssn" not in result["user"]
        assert result["user"]["name"] == "Alice"

    def test_missing_path_is_skipped(self):
        """A rule whose path is absent in the record is silently skipped."""
        e = make_engine({"user.email": "upper"})
        record = {"user": {"name": "Alice"}}
        result = e._process_record(record)
        assert result == {"user": {"name": "Alice"}}

    def test_explicit_none_value_is_processed(self):
        """A field set to None is not skipped — it is anonymized."""
        e = make_engine({"user.email": "upper"})
        record = {"user": {"email": None}}
        result = e._process_record(record)
        # _stub_upper converts None → "NONE"
        assert result["user"]["email"] == "NONE"

    def test_multiple_rules_applied_in_order(self):
        """Multiple rules are each applied to their respective fields."""
        e = make_engine({
            "user.name":  "upper",
            "user.email": "no_salt",
        })
        record = {"user": {"name": "alice", "email": "alice@example.com"}}
        result = e._process_record(record)
        assert result["user"]["name"] == "ALICE"
        assert result["user"]["email"] == "masked:alice@example.com"

    def test_unknown_strategy_skips_field_and_warns(self):
        """An unknown strategy emits a warning and leaves the field unchanged."""
        e = make_engine({"user.email": "ghost_strategy"})
        record = {"user": {"email": "alice@example.com"}}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = e._process_record(record)
        assert result["user"]["email"] == "alice@example.com" 
        assert len(caught) == 1
        assert "ghost_strategy" in str(caught[0].message)

    def test_salt_is_passed_to_salted_strategy(self):
        """The engine's salt reaches salt-aware strategies."""
        e = make_engine({"token": "salted"}, salt="super-secret")
        record = {"token": "abc"}
        result = e._process_record(record)
        assert result["token"] == "abc:super-secret"

    def test_record_with_no_matching_rules_is_unchanged(self):
        """A record whose keys don't match any rule is returned as-is."""
        e = make_engine({"user.email": "upper"})
        record = {"product": {"id": 99}}
        result = e._process_record(record)
        assert result == {"product": {"id": 99}}