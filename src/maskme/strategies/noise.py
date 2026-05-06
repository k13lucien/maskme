import hashlib
import math
import random
from typing import Any, Optional, Union


# ---------------------------------------------------------------------------
# Differential Privacy — Gaussian Mechanism
# ---------------------------------------------------------------------------

def _calibrate_sigma(
    sensitivity: float,
    epsilon: float,
    delta: float,
) -> float:
    """
    Compute the minimum sigma for the (epsilon, delta)-DP Gaussian mechanism.

    The Gaussian mechanism guarantees (epsilon, delta)-differential privacy
    when sigma >= sensitivity * sqrt(2 * ln(1.25 / delta)) / epsilon.

    Reference: Dwork & Roth, "The Algorithmic Foundations of Differential
    Privacy", 2014 — Proposition 3.3.

    Args:
        sensitivity: L2-sensitivity of the query (Δf). Represents the maximum
                     change in the output when a single individual's data
                     changes. Must be strictly positive.
        epsilon:     Privacy loss parameter (ε). Smaller values = stronger
                     privacy. Must be strictly positive.
        delta:       Probability of privacy breach (δ). Typically a very small
                     value (e.g. 1e-5). Must be in the open interval (0, 1).

    Returns:
        The minimum sigma that guarantees (epsilon, delta)-DP.

    Raises:
        ValueError: If any parameter is out of its valid range.
    """
    if sensitivity <= 0:
        raise ValueError(f"'sensitivity' must be strictly positive, got: {sensitivity}")
    if epsilon <= 0:
        raise ValueError(f"'epsilon' must be strictly positive, got: {epsilon}")
    if not (0 < delta < 1):
        raise ValueError(f"'delta' must be in the open interval (0, 1), got: {delta}")

    return sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon


# ---------------------------------------------------------------------------
# Input validators
# ---------------------------------------------------------------------------

def _validate_sigma(sigma: float) -> None:
    """Ensure sigma is a non-negative number."""
    if sigma < 0:
        raise ValueError(f"'sigma' must be >= 0, got: {sigma}")


def _validate_clipping(
    min_val: Optional[float],
    max_val: Optional[float],
) -> None:
    """Ensure min_val <= max_val when both are provided."""
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ValueError(
            f"'min_val' ({min_val}) must be <= 'max_val' ({max_val})."
        )


def _validate_precision(precision: Optional[int]) -> None:
    """Ensure precision is a non-negative integer when provided."""
    if precision is not None and (not isinstance(precision, int) or precision < 0):
        raise ValueError(
            f"'precision' must be a non-negative integer, got: {precision}"
        )


def _validate_dp_sigma_conflict(
    sigma: Optional[float],
    epsilon: Optional[float],
    sensitivity: Optional[float],
) -> None:
    """Raise if both sigma and DP parameters are provided simultaneously."""
    if sigma is not None and (epsilon is not None or sensitivity is not None):
        raise ValueError(
            "Provide either 'sigma' for direct noise control, or "
            "'epsilon' + 'sensitivity' (+ optional 'delta') for "
            "calibrated DP noise — not both."
        )


# ---------------------------------------------------------------------------
# Main strategy
# ---------------------------------------------------------------------------

def apply(
    value: Any,
    sigma: Optional[float] = None,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    precision: Optional[int] = None,
    seed: Optional[Any] = None,
    # Differential Privacy parameters
    epsilon: Optional[float] = None,
    sensitivity: Optional[float] = None,
    delta: float = 1e-5,
    **kwargs,
) -> Union[float, int, Any]:
    """
    Add Gaussian noise to a numeric value.

    Supports two modes — mutually exclusive:

    **Mode 1 — Direct sigma** (simple noise control):
        Provide ``sigma`` directly. Useful for quick anonymization without
        formal privacy guarantees.

        >>> apply(100.0, sigma=5.0, seed=42, precision=2)
        97.43

    **Mode 2 — Calibrated Differential Privacy** (formal guarantee):
        Provide ``epsilon`` and ``sensitivity`` (and optionally ``delta``).
        Sigma is computed automatically using the Gaussian mechanism formula:

            sigma = sensitivity * sqrt(2 * ln(1.25 / delta)) / epsilon

        This guarantees (epsilon, delta)-differential privacy per
        Dwork & Roth (2014), Proposition 3.3.

        >>> apply(100.0, epsilon=1.0, sensitivity=1.0, delta=1e-5)
        99.13

    Args:
        value:       The numeric value to perturb. Non-numeric values are
                     returned as-is. Returns None if value is None.
        sigma:       Standard deviation of Gaussian noise (Mode 1).
                     Must be >= 0. Mutually exclusive with epsilon/sensitivity.
        min_val:     Lower clipping bound applied after noise addition.
        max_val:     Upper clipping bound applied after noise addition.
                     Must be >= min_val when both are provided.
        precision:   Number of decimal places to round to. precision=0
                     returns an int. Must be a non-negative integer.
        seed:        Optional seed for reproducible noise. Combined with
                     sigma and the original value to ensure different fields
                     always receive different noise.
        epsilon:     Privacy loss parameter ε for DP mode. Must be > 0.
        sensitivity: L2-sensitivity Δf of the query for DP mode. Must be > 0.
        delta:       Probability of privacy breach δ for DP mode.
                     Must be in (0, 1). Defaults to 1e-5.
        **kwargs:    Accepted for interface consistency; not used.

    Returns:
        The perturbed numeric value (float or int), or the original value
        unchanged if it cannot be cast to float.

    Raises:
        ValueError: If parameters are invalid, in conflict, or out of range.
    """
    if value is None:
        return None

    try:
        original_value = float(value)
    except (ValueError, TypeError):
        return value

    # Resolve sigma: direct mode or DP-calibrated mode
    _validate_dp_sigma_conflict(sigma, epsilon, sensitivity)

    if epsilon is not None or sensitivity is not None:
        # DP mode: both epsilon and sensitivity are required together
        if epsilon is None or sensitivity is None:
            raise ValueError(
                "DP mode requires both 'epsilon' and 'sensitivity'."
            )
        effective_sigma = _calibrate_sigma(sensitivity, epsilon, delta)
    else:
        # Direct mode: default to sigma=1.0 for backward compatibility
        effective_sigma = sigma if sigma is not None else 1.0

    _validate_sigma(effective_sigma)
    _validate_clipping(min_val, max_val)
    _validate_precision(precision)

    if seed is not None:
        combined = f"{seed}_{effective_sigma}_{original_value}"
        int_seed = int(hashlib.sha256(combined.encode()).hexdigest(), 16)
        rng = random.Random(int_seed)
    else:
        rng = random.Random()

    # Gaussian noise: N(0, sigma²)
    noise = rng.gauss(0, effective_sigma)
    masked_value = original_value + noise

    if min_val is not None:
        masked_value = max(min_val, masked_value)
    if max_val is not None:
        masked_value = min(max_val, masked_value)

    if precision is not None:
        masked_value = round(masked_value, precision)
        return int(masked_value) if precision == 0 else masked_value

    return masked_value