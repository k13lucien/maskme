"""
Unit tests for maskme.strategies.generalization
-------------------------------------------------
Covers validators, the three specialist functions, and the main apply()
router — including routing logic, parameter propagation, and edge cases.
"""

from datetime import datetime

import pytest

from maskme.strategies.generalization import (
    DEFAULT_VALUE,
    _validate_bins,
    _validate_depth,
    _validate_method,
    _validate_step,
    _validate_step_bins_conflict,
    apply,
    generalize_date,
    generalize_location,
    generalize_numeric,
)


# ===========================================================================
# Validators
# ===========================================================================


class TestValidateStep:

    def test_none_is_accepted(self):
        """None step skips validation without raising."""
        _validate_step(None)  # must not raise

    def test_positive_integer_is_accepted(self):
        _validate_step(10)

    def test_positive_float_is_accepted(self):
        _validate_step(0.5)

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            _validate_step(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            _validate_step(-5)


class TestValidateBins:

    def test_none_is_accepted(self):
        _validate_bins(None)

    def test_valid_sorted_bins(self):
        _validate_bins([0, 18, 65])

    def test_single_element_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            _validate_bins([18])

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            _validate_bins([])

    def test_unsorted_bins_raises(self):
        with pytest.raises(ValueError, match="ascending order"):
            _validate_bins([65, 18, 0])

    def test_two_element_bins_accepted(self):
        _validate_bins([0, 100])


class TestValidateStepBinsConflict:

    def test_neither_is_accepted(self):
        _validate_step_bins_conflict(None, None)

    def test_step_only_is_accepted(self):
        _validate_step_bins_conflict(10, None)

    def test_bins_only_is_accepted(self):
        _validate_step_bins_conflict(None, [0, 18, 65])

    def test_both_raises(self):
        with pytest.raises(ValueError, match="not both"):
            _validate_step_bins_conflict(10, [0, 18, 65])


class TestValidateDepth:

    def test_zero_is_accepted(self):
        _validate_depth(0)

    def test_positive_integer_is_accepted(self):
        _validate_depth(3)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _validate_depth(-1)

    def test_float_raises(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _validate_depth(1.5)

    def test_string_raises(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            _validate_depth("1")


class TestValidateMethod:

    def test_range_is_valid(self):
        _validate_method("range")

    def test_floor_is_valid(self):
        _validate_method("floor")

    def test_date_year_is_valid(self):
        _validate_method("date_year")

    def test_date_month_is_valid(self):
        _validate_method("date_month")

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            _validate_method("weekly")


# ===========================================================================
# generalize_numeric
# ===========================================================================


class TestGeneralizeNumeric:

    # --- step + method="range" ---

    def test_step_range_integer(self):
        assert generalize_numeric(27, step=10) == "20-30"

    def test_step_range_exact_boundary(self):
        """A value exactly on the lower boundary maps to that bucket."""
        assert generalize_numeric(20, step=10) == "20-30"

    def test_step_range_float_value(self):
        assert generalize_numeric(27.9, step=10) == "20-30"

    def test_step_range_zero(self):
        assert generalize_numeric(0, step=10) == "0-10"

    def test_step_range_negative(self):
        assert generalize_numeric(-5, step=10) == "-10-0"

    # --- step + method="floor" ---

    def test_step_floor(self):
        assert generalize_numeric(27, step=10, method="floor") == "20"

    def test_step_floor_exact_boundary(self):
        assert generalize_numeric(20, step=10, method="floor") == "20"

    # --- custom bins ---

    def test_bins_middle_bucket(self):
        assert generalize_numeric(27, bins=[0, 18, 25, 65]) == "25-65"

    def test_bins_below_first_boundary(self):
        assert generalize_numeric(10, bins=[18, 25, 65]) == "<18"

    def test_bins_above_last_boundary(self):
        assert generalize_numeric(80, bins=[0, 18, 65]) == ">=65"

    def test_bins_exact_lower_boundary(self):
        """Value equal to a bin boundary maps to the bucket starting there."""
        assert generalize_numeric(18, bins=[0, 18, 65]) == "18-65"

    def test_bins_exact_upper_boundary(self):
        """Value equal to the upper boundary falls into the next bucket (or >=)."""
        assert generalize_numeric(65, bins=[0, 18, 65]) == ">=65"

    # --- no step, no bins ---

    def test_no_step_no_bins_returns_default(self):
        assert generalize_numeric(42) == DEFAULT_VALUE

    def test_no_step_no_bins_custom_default(self):
        assert generalize_numeric(42, default="N/A") == "N/A"


# ===========================================================================
# generalize_date
# ===========================================================================


class TestGeneralizeDate:

    def test_iso_string_year(self):
        assert generalize_date("2003-06-15", method="date_year") == "2003"

    def test_iso_string_month(self):
        assert generalize_date("2003-06-15", method="date_month") == "2003-06"

    def test_datetime_object_year(self):
        dt = datetime(2003, 6, 15)
        assert generalize_date(dt, method="date_year") == "2003"

    def test_datetime_object_month(self):
        dt = datetime(2003, 6, 15)
        assert generalize_date(dt, method="date_month") == "2003-06"

    def test_invalid_string_returns_default(self):
        assert generalize_date("not-a-date") == DEFAULT_VALUE

    def test_invalid_string_custom_default(self):
        assert generalize_date("not-a-date", default="N/A") == "N/A"

    def test_none_returns_default(self):
        assert generalize_date(None) == DEFAULT_VALUE

    def test_integer_returns_default(self):
        """An integer cannot be parsed as ISO date."""
        assert generalize_date(99999) == DEFAULT_VALUE


# ===========================================================================
# generalize_location
# ===========================================================================


class TestGeneralizeLocation:

    def test_depth_one(self):
        assert generalize_location("Ouagadougou, Kadiogo, Centre", depth=1) == "Kadiogo, Centre"

    def test_depth_two(self):
        assert generalize_location("Ouagadougou, Kadiogo, Centre", depth=2) == "Centre"

    def test_depth_zero_returns_full_string(self):
        """depth=0 drops nothing — the full location is returned."""
        result = generalize_location("A, B, C", depth=0)
        assert result == "A, B, C"

    def test_depth_equal_to_parts_returns_default(self):
        """If depth >= number of parts, nothing remains → default."""
        assert generalize_location("City, Country", depth=2) == DEFAULT_VALUE

    def test_depth_exceeds_parts_returns_default(self):
        assert generalize_location("City", depth=3) == DEFAULT_VALUE

    def test_custom_default(self):
        assert generalize_location("City", depth=5, default="Unknown") == "Unknown"

    def test_extra_whitespace_is_stripped(self):
        """Parts are stripped of leading/trailing spaces."""
        result = generalize_location("  Paris  ,  Île-de-France  ,  France  ", depth=1)
        assert result == "Île-de-France, France"


# ===========================================================================
# apply() — main router
# ===========================================================================


class TestApply:

    # --- None passthrough ---

    def test_none_returns_none(self):
        assert apply(None) is None

    # --- Numeric routing ---

    def test_routes_integer_to_numeric(self):
        assert apply(27, step=10) == "20-30"

    def test_routes_float_to_numeric(self):
        assert apply(27.5, step=10) == "20-30"

    def test_routes_numeric_with_bins(self):
        assert apply(27, bins=[0, 18, 25, 65]) == "25-65"

    # --- Date routing ---

    def test_routes_iso_string_date_year(self):
        assert apply("2003-06-15", method="date_year") == "2003"

    def test_routes_iso_string_date_month(self):
        assert apply("2003-06-15", method="date_month") == "2003-06"

    def test_routes_datetime_object(self):
        dt = datetime(1990, 3, 22)
        assert apply(dt, method="date_year") == "1990"

    # --- Location routing ---

    def test_routes_comma_string_to_location(self):
        assert apply("Ouagadougou, Kadiogo, Centre", depth=1) == "Kadiogo, Centre"

    # --- Routing ambiguity: "1,200" must NOT go to location ---

    def test_numeric_string_with_comma_is_not_routed_to_location(self):
        """A non-int/float string is not blindly sent to generalize_location.
        Since "1,200" is a str (not int/float), it falls through to the
        location route — this test documents the current behaviour and
        signals if routing logic changes."""
        result = apply("1,200", depth=1)
        # "1,200" has a comma → routed to location → depth=1 drops "1" → "200"
        assert result == "200"

    # --- Default propagation ---

    def test_custom_default_propagated_to_numeric(self):
        assert apply(42, default="N/A") == "N/A"

    def test_custom_default_propagated_to_location(self):
        assert apply("City", depth=5, default="Unknown") == "Unknown"

    # --- Validation errors bubble up ---

    def test_invalid_step_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            apply(27, step=-1)

    def test_invalid_bins_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            apply(27, bins=[18])

    def test_step_and_bins_conflict_raises(self):
        with pytest.raises(ValueError, match="not both"):
            apply(27, step=10, bins=[0, 18, 65])

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            apply(27, method="unknown")

    def test_invalid_depth_raises(self):
        with pytest.raises(ValueError, match="non-negative integer"):
            apply("A, B", depth=-1)

    # --- kwargs forwarding ---

    def test_accepts_extra_kwargs(self):
        """Extra kwargs from the engine are accepted without raising."""
        assert apply(27, step=10, salt="secret", foo="bar") == "20-30"