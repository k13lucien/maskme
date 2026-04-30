"""
Core test suite for the generalization strategy.

All tests go through the public apply() interface only.
Coverage focuses on the most critical behaviors:
  - None passthrough
  - Numeric generalization (step and bins)
  - Date generalization (all 4 methods)
  - Location generalization
  - Parameter validation (errors)
  - Fallback to DEFAULT_VALUE
"""

import pytest
from datetime import datetime
from maskme.strategies.generalization import DEFAULT_VALUE, apply


# ===========================================================================
# None passthrough
# ===========================================================================

def test_none_returns_none():
    assert apply(None) is None


# ===========================================================================
# Numeric — step
# ===========================================================================

class TestNumericStep:
    def test_basic_range(self):
        assert apply(27, step=10) == "20-30"

    def test_lower_bound_is_inclusive(self):
        assert apply(20, step=10) == "20-30"

    def test_floor_method(self):
        assert apply(27, step=10, method="floor") == "20"

    def test_zero_value(self):
        assert apply(0, step=10) == "0-10"

    def test_float_value(self):
        assert apply(27.9, step=10) == "20-30"


# ===========================================================================
# Numeric — bins
# ===========================================================================

class TestNumericBins:
    BINS = [0, 18, 25, 65]

    def test_value_in_middle_interval(self):
        assert apply(27, bins=self.BINS) == "25-65"

    def test_value_on_lower_boundary(self):
        assert apply(18, bins=self.BINS) == "18-25"

    def test_value_below_first_bin(self):
        assert apply(-1, bins=self.BINS) == "<0"

    def test_value_above_last_bin(self):
        assert apply(80, bins=self.BINS) == ">=65"

    def test_value_on_last_bin_boundary(self):
        assert apply(65, bins=self.BINS) == ">=65"


# ===========================================================================
# Date generalization
# ===========================================================================

class TestDate:
    DATE = "2003-06-15"

    def test_year(self):
        assert apply(self.DATE, method="date_year") == "2003"

    def test_month(self):
        assert apply(self.DATE, method="date_month") == "2003-06"

    def test_datetime_object(self):
        assert apply(datetime(2003, 6, 15), method="date_year") == "2003"


# ===========================================================================
# Location generalization
# ===========================================================================

class TestLocation:
    LOC = "Ouagadougou, Kadiogo, Centre"

    def test_depth_1(self):
        assert apply(self.LOC, depth=1) == "Kadiogo, Centre"

    def test_depth_2(self):
        assert apply(self.LOC, depth=2) == "Centre"

    def test_depth_exceeds_parts_returns_default(self):
        assert apply(self.LOC, depth=10) == DEFAULT_VALUE


# ===========================================================================
# Fallback
# ===========================================================================

def test_unrecognized_string_returns_default():
    assert apply("something_unknown") == DEFAULT_VALUE


# ===========================================================================
# Validation errors
# ===========================================================================

class TestValidationErrors:
    def test_negative_step_raises(self):
        with pytest.raises(ValueError):
            apply(27, step=-10)

    def test_step_and_bins_together_raises(self):
        with pytest.raises(ValueError):
            apply(27, step=10, bins=[0, 18, 65])

    def test_unsorted_bins_raises(self):
        with pytest.raises(ValueError):
            apply(27, bins=[65, 18, 0])

    def test_negative_depth_raises(self):
        with pytest.raises(ValueError):
            apply("A, B", depth=-1)

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError):
            apply(27, method="unknown")