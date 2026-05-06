"""
Integration tests for the full MaskMe workflow
------------------------------------------------
These tests exercise the real engine with the real strategy registry.
No stubs — every call goes through MaskMe.mask() → _process_record()
→ strategy function, validating that all layers work together correctly.

Scenarios covered:
  - Each registered strategy end-to-end
  - Nested paths and dot-notation traversal
  - Field deletion via the drop strategy
  - Parameterized strategies (dict config)
  - Multiple rules applied to a single record
  - Realistic anonymization datasets
  - Generator laziness and deepcopy safety
  - Unknown strategy warning propagation
  - Differential Privacy noise mode through the engine
"""

import warnings
from datetime import datetime

import pytest

from maskme.core.engine import MaskMe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_RECORD = {
    "id": "u-001",
    "personal": {
        "name": "Alice Ouédraogo",
        "email": "alice@example.com",
        "phone": "0612345678",
        "birth_date": "1990-06-15",
        "ssn": "290066312345678",
        "location": "Ouagadougou, Kadiogo, Centre",
    },
    "finance": {
        "salary": 75000.0,
        "card_number": "4111111111111234",
    },
    "metadata": {
        "created_at": "2024-01-15",
        "score": 92,
    },
}


@pytest.fixture
def user_record():
    """Return a deep copy of USER_RECORD for each test."""
    import copy
    return copy.deepcopy(USER_RECORD)


# ===========================================================================
# Each strategy end-to-end
# ===========================================================================


class TestEachStrategy:
    """One test per registered strategy — validates engine ↔ strategy wiring."""

    def test_hash_strategy(self):
        """'hash' strategy hashes the target field."""
        engine = MaskMe(rules={"personal.email": "hash"}, salt="secret")
        result = next(engine.mask([{"personal": {"email": "alice@example.com"}}]))
        hashed = result["personal"]["email"]
        assert isinstance(hashed, str)
        assert hashed != "alice@example.com"
        assert len(hashed) == 64  # sha256 hex digest

    def test_redact_strategy(self):
        """'redact' strategy replaces characters with the placeholder."""
        engine = MaskMe(rules={"personal.phone": "redact"})
        result = next(engine.mask([{"personal": {"phone": "0612345678"}}]))
        assert result["personal"]["phone"] == "*" * 10

    def test_noise_strategy(self):
        """'noise' strategy perturbs numeric values."""
        engine = MaskMe(rules={"finance.salary": "noise"})
        result = next(engine.mask([{"finance": {"salary": 75000.0}}]))
        assert isinstance(result["finance"]["salary"], float)
        assert result["finance"]["salary"] != 75000.0

    def test_generalize_strategy(self):
        """'generalize' strategy buckets a numeric value."""
        engine = MaskMe(rules={"metadata.score": {"strategy": "generalize", "step": 10}})
        result = next(engine.mask([{"metadata": {"score": 92}}]))
        assert result["metadata"]["score"] == "90-100"

    def test_keep_strategy(self):
        """'keep' strategy leaves the value identical."""
        engine = MaskMe(rules={"id": "keep"})
        record = {"id": "u-001"}
        result = next(engine.mask([record]))
        assert result["id"] == "u-001"

    def test_drop_strategy(self):
        """'drop' strategy removes the field entirely from the record."""
        engine = MaskMe(rules={"personal.ssn": "drop"})
        record = {"personal": {"ssn": "290066312345678", "name": "Alice"}}
        result = next(engine.mask([record]))
        assert "ssn" not in result["personal"]
        assert result["personal"]["name"] == "Alice"


# ===========================================================================
# Parameterized strategies (dict config)
# ===========================================================================


class TestParameterizedStrategies:

    def test_hash_with_custom_algo(self):
        """Engine forwards 'algo' param to the hash strategy."""
        engine = MaskMe(rules={"email": {"strategy": "hash", "algo": "sha512"}}, salt="s")
        result = next(engine.mask([{"email": "alice@example.com"}]))
        assert len(result["email"]) == 128  # sha512 hex digest

    def test_redact_with_keep_start_and_end(self):
        """Engine forwards keep_start and keep_end to the redact strategy."""
        engine = MaskMe(rules={
            "card": {"strategy": "redact", "char": "#", "keep_start": 0, "keep_end": 4}
        })
        result = next(engine.mask([{"card": "4111111111111234"}]))
        assert result["card"] == "############1234"

    def test_generalize_with_bins(self):
        """Engine forwards bins param to the generalize strategy."""
        engine = MaskMe(rules={
            "age": {"strategy": "generalize", "bins": [0, 18, 35, 65]}
        })
        result = next(engine.mask([{"age": 27}]))
        assert result["age"] == "18-35"

    def test_generalize_date(self):
        """Engine forwards method param for date generalization."""
        engine = MaskMe(rules={
            "birth_date": {"strategy": "generalize", "method": "date_year"}
        })
        result = next(engine.mask([{"birth_date": "1990-06-15"}]))
        assert result["birth_date"] == "1990"

    def test_generalize_location(self):
        """Engine forwards depth param for location generalization."""
        engine = MaskMe(rules={
            "location": {"strategy": "generalize", "depth": 1}
        })
        result = next(engine.mask([{"location": "Ouagadougou, Kadiogo, Centre"}]))
        assert result["location"] == "Kadiogo, Centre"

    def test_noise_with_seed_and_precision(self):
        """Engine forwards seed and precision to the noise strategy."""
        engine = MaskMe(rules={
            "salary": {"strategy": "noise", "sigma": 100.0, "seed": 42, "precision": 2}
        })
        result = next(engine.mask([{"salary": 75000.0}]))
        assert isinstance(result["salary"], float)
        assert round(result["salary"], 2) == result["salary"]

    def test_noise_dp_mode(self):
        """Engine forwards epsilon, sensitivity, delta for DP-calibrated noise."""
        engine = MaskMe(rules={
            "salary": {
                "strategy": "noise",
                "epsilon": 1.0,
                "sensitivity": 1000.0,
                "delta": 1e-5,
                "seed": 99,
                "precision": 0,
            }
        })
        result = next(engine.mask([{"salary": 75000.0}]))
        assert isinstance(result["salary"], int)


# ===========================================================================
# Nested paths
# ===========================================================================


class TestNestedPaths:

    def test_two_level_path(self):
        engine = MaskMe(rules={"personal.email": "hash"}, salt="s")
        record = {"personal": {"email": "alice@example.com", "name": "Alice"}}
        result = next(engine.mask([record]))
        assert result["personal"]["email"] != "alice@example.com"
        assert result["personal"]["name"] == "Alice"

    def test_three_level_path(self):
        engine = MaskMe(rules={"a.b.c": "redact"})
        record = {"a": {"b": {"c": "secret", "d": "visible"}}}
        result = next(engine.mask([record]))
        assert result["a"]["b"]["c"] == "******"
        assert result["a"]["b"]["d"] == "visible"

    def test_absent_path_is_skipped(self):
        """A rule whose path does not exist in the record is silently skipped."""
        engine = MaskMe(rules={"personal.fax": "redact"})
        record = {"personal": {"email": "alice@example.com"}}
        result = next(engine.mask([record]))
        assert result == {"personal": {"email": "alice@example.com"}}

    def test_drop_nested_field(self):
        engine = MaskMe(rules={"personal.ssn": "drop"})
        record = {"personal": {"ssn": "123", "name": "Alice"}}
        result = next(engine.mask([record]))
        assert "ssn" not in result["personal"]


# ===========================================================================
# Multiple rules on a single record
# ===========================================================================


class TestMultipleRules:

    def test_all_strategies_on_one_record(self, user_record):
        """A realistic rule set applies all strategies correctly on one record."""
        rules = {
            "personal.email":     "hash",
            "personal.phone":     "redact",
            "personal.ssn":       "drop",
            "personal.birth_date": {"strategy": "generalize", "method": "date_year"},
            "personal.location":  {"strategy": "generalize", "depth": 1},
            "finance.salary":     {"strategy": "noise", "sigma": 100.0, "seed": 1, "precision": 0},
            "finance.card_number": {"strategy": "redact", "keep_end": 4},
            "metadata.score":     {"strategy": "generalize", "step": 10},
            "id":                 "keep",
        }
        engine = MaskMe(rules=rules, salt="integration-salt")
        result = next(engine.mask([user_record]))

        # hash
        assert len(result["personal"]["email"]) == 64
        # redact
        assert result["personal"]["phone"] == "*" * 10
        # drop
        assert "ssn" not in result["personal"]
        # generalize date
        assert result["personal"]["birth_date"] == "1990"
        # generalize location
        assert result["personal"]["location"] == "Kadiogo, Centre"
        # noise (int due to precision=0)
        assert isinstance(result["finance"]["salary"], int)
        # redact card (keep last 4)
        assert result["finance"]["card_number"].endswith("1234")
        assert result["finance"]["card_number"].startswith("*")
        # generalize score
        assert result["metadata"]["score"] == "90-100"
        # keep
        assert result["id"] == "u-001"

    def test_rules_do_not_interfere_with_each_other(self):
        """Applying a rule on one field does not affect sibling fields."""
        rules = {"a": "redact", "b": "keep"}
        engine = MaskMe(rules=rules)
        record = {"a": "secret", "b": "visible"}
        result = next(engine.mask([record]))
        assert result["a"] == "******"
        assert result["b"] == "visible"


# ===========================================================================
# Generator behaviour
# ===========================================================================


class TestGeneratorBehaviour:

    def test_processes_multiple_records(self):
        """mask() yields one anonymized record per input record."""
        engine = MaskMe(rules={"email": "hash"}, salt="s")
        records = [{"email": f"user{i}@example.com"} for i in range(5)]
        results = list(engine.mask(records))
        assert len(results) == 5

    def test_each_record_independently_anonymized(self):
        """Different input values produce different hashes."""
        engine = MaskMe(rules={"email": "hash"}, salt="s")
        records = [{"email": "alice@example.com"}, {"email": "bob@example.com"}]
        results = list(engine.mask(records))
        assert results[0]["email"] != results[1]["email"]

    def test_same_value_same_hash_across_records(self):
        """The same value always produces the same hash (determinism)."""
        engine = MaskMe(rules={"email": "hash"}, salt="s")
        records = [{"email": "alice@example.com"}, {"email": "alice@example.com"}]
        results = list(engine.mask(records))
        assert results[0]["email"] == results[1]["email"]

    def test_original_records_not_mutated(self):
        """deepcopy ensures the caller's original data is never modified."""
        engine = MaskMe(rules={"personal.email": "hash"}, salt="s")
        original = {"personal": {"email": "alice@example.com"}}
        records = [original]
        list(engine.mask(records))
        assert original["personal"]["email"] == "alice@example.com"

    def test_accepts_generator_input(self):
        """mask() handles a generator as input (not just a list)."""
        engine = MaskMe(rules={"name": "redact"})
        gen = ({"name": f"user_{i}"} for i in range(3))
        results = list(engine.mask(gen))
        assert len(results) == 3
        assert all("name" in r for r in results)

    def test_empty_input_yields_nothing(self):
        engine = MaskMe(rules={"email": "hash"})
        assert list(engine.mask([])) == []


# ===========================================================================
# Unknown strategy warning
# ===========================================================================


class TestUnknownStrategy:

    def test_unknown_strategy_emits_warning(self):
        """An unregistered strategy name triggers a UserWarning."""
        engine = MaskMe(rules={"email": "ghost_strategy"})
        record = {"email": "alice@example.com"}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = next(engine.mask([record]))
        assert len(caught) == 1
        assert issubclass(caught[0].category, UserWarning)
        assert "ghost_strategy" in str(caught[0].message)

    def test_unknown_strategy_leaves_field_unchanged(self):
        """An unknown strategy does not modify the field."""
        engine = MaskMe(rules={"email": "ghost_strategy"})
        record = {"email": "alice@example.com"}
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = next(engine.mask([record]))
        assert result["email"] == "alice@example.com"


# ===========================================================================
# Salt propagation
# ===========================================================================


class TestSaltPropagation:

    def test_different_salts_produce_different_hashes(self):
        """The global salt is forwarded to the hash strategy."""
        engine_a = MaskMe(rules={"email": "hash"}, salt="salt-a")
        engine_b = MaskMe(rules={"email": "hash"}, salt="salt-b")
        record = {"email": "alice@example.com"}
        result_a = next(engine_a.mask([record]))
        result_b = next(engine_b.mask([record]))
        assert result_a["email"] != result_b["email"]

    def test_same_salt_produces_same_hash(self):
        """Two engines with the same salt produce identical hashes."""
        engine_a = MaskMe(rules={"email": "hash"}, salt="shared")
        engine_b = MaskMe(rules={"email": "hash"}, salt="shared")
        record = {"email": "alice@example.com"}
        result_a = next(engine_a.mask([record]))
        result_b = next(engine_b.mask([record]))
        assert result_a["email"] == result_b["email"]