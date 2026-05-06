"""
Unit tests for maskme.strategies.noise
----------------------------------------
Covers validators, _calibrate_sigma, both apply() modes (direct sigma
and DP-calibrated), clipping, precision, seed reproducibility, thread
safety, and edge-case inputs.
"""

import math
import random
import threading
from typing import Any

import pytest

from maskme.strategies.noise import (
    _calibrate_sigma,
    _validate_clipping,
    _validate_dp_sigma_conflict,
    _validate_precision,
    _validate_sigma,
    apply,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _expected_sigma(sensitivity: float, epsilon: float, delta: float) -> float:
    """Recompute calibrated sigma independently of the strategy."""
    return sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon


# ===========================================================================
# _calibrate_sigma
# ===========================================================================


class TestCalibrateSigma:

    def test_matches_formula(self):
        """Output matches the reference formula directly."""
        result = _calibrate_sigma(sensitivity=1.0, epsilon=1.0, delta=1e-5)
        assert result == pytest.approx(_expected_sigma(1.0, 1.0, 1e-5))

    def test_higher_epsilon_smaller_sigma(self):
        """Stronger epsilon (less privacy loss) requires less noise."""
        sigma_loose = _calibrate_sigma(1.0, epsilon=0.1, delta=1e-5)
        sigma_tight = _calibrate_sigma(1.0, epsilon=1.0, delta=1e-5)
        assert sigma_loose > sigma_tight

    def test_higher_sensitivity_larger_sigma(self):
        """Higher sensitivity requires more noise to preserve privacy."""
        sigma_low = _calibrate_sigma(sensitivity=1.0, epsilon=1.0, delta=1e-5)
        sigma_high = _calibrate_sigma(sensitivity=10.0, epsilon=1.0, delta=1e-5)
        assert sigma_high > sigma_low

    def test_smaller_delta_larger_sigma(self):
        """Tighter delta (lower breach probability) requires more noise."""
        sigma_loose = _calibrate_sigma(1.0, 1.0, delta=1e-2)
        sigma_tight = _calibrate_sigma(1.0, 1.0, delta=1e-8)
        assert sigma_tight > sigma_loose

    def test_returns_positive_float(self):
        """Calibrated sigma is always strictly positive."""
        result = _calibrate_sigma(1.0, 1.0, 1e-5)
        assert result > 0

    # --- Invalid inputs ---

    def test_zero_sensitivity_raises(self):
        with pytest.raises(ValueError, match="sensitivity"):
            _calibrate_sigma(sensitivity=0.0, epsilon=1.0, delta=1e-5)

    def test_negative_sensitivity_raises(self):
        with pytest.raises(ValueError, match="sensitivity"):
            _calibrate_sigma(sensitivity=-1.0, epsilon=1.0, delta=1e-5)

    def test_zero_epsilon_raises(self):
        with pytest.raises(ValueError, match="epsilon"):
            _calibrate_sigma(sensitivity=1.0, epsilon=0.0, delta=1e-5)

    def test_negative_epsilon_raises(self):
        with pytest.raises(ValueError, match="epsilon"):
            _calibrate_sigma(sensitivity=1.0, epsilon=-0.5, delta=1e-5)

    def test_delta_zero_raises(self):
        with pytest.raises(ValueError, match="delta"):
            _calibrate_sigma(sensitivity=1.0, epsilon=1.0, delta=0.0)

    def test_delta_one_raises(self):
        with pytest.raises(ValueError, match="delta"):
            _calibrate_sigma(sensitivity=1.0, epsilon=1.0, delta=1.0)

    def test_delta_above_one_raises(self):
        with pytest.raises(ValueError, match="delta"):
            _calibrate_sigma(sensitivity=1.0, epsilon=1.0, delta=1.5)


# ===========================================================================
# Validators
# ===========================================================================


class TestValidateSigma:

    def test_positive_is_valid(self):
        _validate_sigma(1.0)

    def test_zero_is_valid(self):
        """sigma=0 produces no noise — valid but equivalent to noop."""
        _validate_sigma(0.0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="sigma"):
            _validate_sigma(-0.1)


class TestValidateClipping:

    def test_both_none_is_valid(self):
        _validate_clipping(None, None)

    def test_only_min_is_valid(self):
        _validate_clipping(0.0, None)

    def test_only_max_is_valid(self):
        _validate_clipping(None, 100.0)

    def test_min_less_than_max_is_valid(self):
        _validate_clipping(0.0, 100.0)

    def test_min_equal_max_is_valid(self):
        """min == max clamps all values to a single point — valid edge case."""
        _validate_clipping(50.0, 50.0)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min_val"):
            _validate_clipping(100.0, 10.0)


class TestValidatePrecision:

    def test_none_is_valid(self):
        _validate_precision(None)

    def test_zero_is_valid(self):
        _validate_precision(0)

    def test_positive_integer_is_valid(self):
        _validate_precision(3)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="precision"):
            _validate_precision(-1)

    def test_float_raises(self):
        with pytest.raises(ValueError, match="precision"):
            _validate_precision(1.5)


class TestValidateDpSigmaConflict:

    def test_sigma_only_is_valid(self):
        _validate_dp_sigma_conflict(sigma=1.0, epsilon=None, sensitivity=None)

    def test_dp_params_only_is_valid(self):
        _validate_dp_sigma_conflict(sigma=None, epsilon=1.0, sensitivity=1.0)

    def test_all_none_is_valid(self):
        _validate_dp_sigma_conflict(sigma=None, epsilon=None, sensitivity=None)

    def test_sigma_and_epsilon_raises(self):
        with pytest.raises(ValueError, match="not both"):
            _validate_dp_sigma_conflict(sigma=1.0, epsilon=1.0, sensitivity=None)

    def test_sigma_and_sensitivity_raises(self):
        with pytest.raises(ValueError, match="not both"):
            _validate_dp_sigma_conflict(sigma=1.0, epsilon=None, sensitivity=1.0)

    def test_sigma_and_both_dp_params_raises(self):
        with pytest.raises(ValueError, match="not both"):
            _validate_dp_sigma_conflict(sigma=1.0, epsilon=1.0, sensitivity=1.0)


# ===========================================================================
# apply() — Mode 1: direct sigma
# ===========================================================================


class TestApplyDirectSigma:

    def test_returns_float(self):
        """Default output is float."""
        result = apply(100.0, sigma=1.0, seed=42)
        assert isinstance(result, float)

    def test_sigma_zero_returns_original(self):
        """With sigma=0, noise=0 — output equals input."""
        assert apply(100.0, sigma=0.0) == pytest.approx(100.0)

    def test_output_differs_from_input(self):
        """With non-zero sigma, noise is added. Seed is fixed for determinism."""
        result = apply(100.0, sigma=5.0, seed=1)
        assert result != 100.0

    def test_default_sigma_is_one(self):
        """Omitting sigma defaults to sigma=1.0."""
        r1 = apply(100.0, seed=99)
        r2 = apply(100.0, sigma=1.0, seed=99)
        assert r1 == pytest.approx(r2)

    def test_negative_sigma_raises(self):
        with pytest.raises(ValueError, match="sigma"):
            apply(100.0, sigma=-1.0)


# ===========================================================================
# apply() — Mode 2: Differential Privacy
# ===========================================================================


class TestApplyDPMode:

    def test_dp_mode_returns_float(self):
        result = apply(100.0, epsilon=1.0, sensitivity=1.0, delta=1e-5)
        assert isinstance(result, float)

    def test_dp_mode_uses_calibrated_sigma(self):
        """With seed, result is deterministic and matches manual calibration."""
        expected_sigma = _expected_sigma(1.0, 1.0, 1e-5)
        combined = f"42_{expected_sigma}_{100.0}"
        import hashlib, random as _r
        int_seed = int(hashlib.sha256(combined.encode()).hexdigest(), 16)
        rng = _r.Random(int_seed)
        expected = 100.0 + rng.gauss(0, expected_sigma)

        result = apply(100.0, epsilon=1.0, sensitivity=1.0, delta=1e-5, seed=42)
        assert result == pytest.approx(expected)

    def test_smaller_epsilon_produces_more_noise_on_average(self):
        """Lower epsilon → larger sigma → higher expected absolute noise.
        Seeds are fixed per sample to make the comparison fully deterministic."""
        n = 500
        noise_tight = [
            abs(apply(0.0, epsilon=0.1, sensitivity=1.0, delta=1e-5, seed=i) - 0.0)
            for i in range(n)
        ]
        noise_loose = [
            abs(apply(0.0, epsilon=2.0, sensitivity=1.0, delta=1e-5, seed=i) - 0.0)
            for i in range(n)
        ]
        assert sum(noise_tight) / n > sum(noise_loose) / n

    def test_epsilon_only_raises(self):
        """epsilon without sensitivity is incomplete — must raise."""
        with pytest.raises(ValueError, match="sensitivity"):
            apply(100.0, epsilon=1.0)

    def test_sensitivity_only_raises(self):
        """sensitivity without epsilon is incomplete — must raise."""
        with pytest.raises(ValueError, match="epsilon"):
            apply(100.0, sensitivity=1.0)

    def test_sigma_and_epsilon_conflict_raises(self):
        with pytest.raises(ValueError, match="not both"):
            apply(100.0, sigma=1.0, epsilon=1.0, sensitivity=1.0)

    def test_default_delta_is_1e5(self):
        """Omitting delta uses the 1e-5 default."""
        r1 = apply(100.0, epsilon=1.0, sensitivity=1.0, seed=1)
        r2 = apply(100.0, epsilon=1.0, sensitivity=1.0, delta=1e-5, seed=1)
        assert r1 == pytest.approx(r2)

    def test_invalid_delta_raises(self):
        with pytest.raises(ValueError, match="delta"):
            apply(100.0, epsilon=1.0, sensitivity=1.0, delta=0.0)


# ===========================================================================
# apply() — Clipping
# ===========================================================================


class TestApplyClipping:

    def test_min_clipping(self):
        """Output is never below min_val."""
        for _ in range(50):
            result = apply(0.0, sigma=100.0, min_val=0.0)
            assert result >= 0.0

    def test_max_clipping(self):
        """Output is never above max_val."""
        for _ in range(50):
            result = apply(100.0, sigma=100.0, max_val=100.0)
            assert result <= 100.0

    def test_min_and_max_clipping(self):
        """Output stays within [min_val, max_val]."""
        for _ in range(50):
            result = apply(50.0, sigma=100.0, min_val=0.0, max_val=100.0)
            assert 0.0 <= result <= 100.0

    def test_invalid_clipping_raises(self):
        with pytest.raises(ValueError, match="min_val"):
            apply(50.0, sigma=1.0, min_val=100.0, max_val=10.0)


# ===========================================================================
# apply() — Precision
# ===========================================================================


class TestApplyPrecision:

    def test_precision_two_decimal_places(self):
        result = apply(100.0, sigma=5.0, seed=1, precision=2)
        assert isinstance(result, float)
        assert round(result, 2) == result

    def test_precision_zero_returns_int(self):
        result = apply(100.0, sigma=5.0, seed=1, precision=0)
        assert isinstance(result, int)

    def test_precision_negative_raises(self):
        with pytest.raises(ValueError, match="precision"):
            apply(100.0, sigma=1.0, precision=-1)

    def test_precision_float_raises(self):
        with pytest.raises(ValueError, match="precision"):
            apply(100.0, sigma=1.0, precision=1.5)


# ===========================================================================
# apply() — Seed reproducibility
# ===========================================================================


class TestApplySeed:

    def test_same_seed_same_result(self):
        """Same seed + same value always produces the same output."""
        r1 = apply(100.0, sigma=5.0, seed=42)
        r2 = apply(100.0, sigma=5.0, seed=42)
        assert r1 == pytest.approx(r2)

    def test_different_seeds_different_results(self):
        r1 = apply(100.0, sigma=5.0, seed=1)
        r2 = apply(100.0, sigma=5.0, seed=2)
        assert r1 != pytest.approx(r2)

    def test_same_seed_different_values_different_noise(self):
        """Two fields with the same seed and sigma receive different noise."""
        r1 = apply(100.0, sigma=5.0, seed=42)
        r2 = apply(200.0, sigma=5.0, seed=42)
        noise1 = r1 - 100.0
        noise2 = r2 - 200.0
        assert noise1 != pytest.approx(noise2)

    def test_no_seed_is_non_deterministic(self):
        """Without a seed, two calls produce different results (probabilistic)."""
        results = {apply(100.0, sigma=5.0) for _ in range(20)}
        assert len(results) > 1


# ===========================================================================
# apply() — Thread safety
# ===========================================================================


class TestThreadSafety:

    def test_does_not_corrupt_global_random_state(self):
        """Calling apply() must not alter the global random.random() sequence."""
        random.seed(0)
        baseline = [random.random() for _ in range(10)]

        random.seed(0)
        apply(100.0, sigma=5.0, seed=42)  # must not touch global state
        after = [random.random() for _ in range(10)]

        assert baseline == after

    def test_concurrent_calls_do_not_raise(self):
        """Multiple threads calling apply() simultaneously must not raise."""
        errors = []

        def worker():
            try:
                for _ in range(50):
                    apply(100.0, sigma=1.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


# ===========================================================================
# apply() — Edge-case inputs
# ===========================================================================


class TestApplyEdgeCases:

    def test_none_returns_none(self):
        assert apply(None) is None

    def test_non_numeric_string_returned_as_is(self):
        assert apply("not_a_number") == "not_a_number"

    def test_integer_input(self):
        result = apply(42, sigma=1.0)
        assert isinstance(result, float)

    def test_string_numeric_input(self):
        """A string that represents a number is cast to float."""
        result = apply("100.5", sigma=0.0)
        assert result == pytest.approx(100.5)

    def test_boolean_true_treated_as_one(self):
        """True is cast to 1.0 in Python."""
        result = apply(True, sigma=0.0)
        assert result == pytest.approx(1.0)

    def test_accepts_extra_kwargs(self):
        """Extra kwargs forwarded by the engine are accepted without raising."""
        result = apply(100.0, sigma=1.0, seed=1, salt="secret", foo="bar")
        assert isinstance(result, float)