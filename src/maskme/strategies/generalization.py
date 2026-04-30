import math
from typing import Any, Union, List, Optional
from datetime import datetime
 
 
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
 
DATE_METHODS = {
    "date_year":    lambda dt: str(dt.year),
    "date_month":   lambda dt: dt.strftime("%Y-%m"),
}
 
DEFAULT_VALUE = "Others"
 
 
# ---------------------------------------------------------------------------
# Input Validators
# ---------------------------------------------------------------------------
 
def _validate_step(step: Optional[Union[int, float]]) -> None:
    """Ensure step is a strictly positive number."""
    if step is not None and step <= 0:
        raise ValueError(f"'step' must be strictly positive, got: {step}")
 
 
def _validate_bins(bins: Optional[List[float]]) -> None:
    """Ensure bins has at least two boundaries and is sorted in ascending order."""
    if bins is None:
        return
    if len(bins) < 2:
        raise ValueError("'bins' must contain at least 2 boundary values.")
    if bins != sorted(bins):
        raise ValueError("'bins' must be sorted in ascending order.")
 
 
def _validate_step_bins_conflict(
    step: Optional[Union[int, float]],
    bins: Optional[List[float]],
) -> None:
    """Raise an error if both step and bins are provided at the same time."""
    if step is not None and bins is not None:
        raise ValueError("Provide either 'step' or 'bins', not both.")
 
 
def _validate_depth(depth: int) -> None:
    """Ensure depth is a non-negative integer."""
    if not isinstance(depth, int) or depth < 0:
        raise ValueError(f"'depth' must be a non-negative integer, got: {depth}")
 
 
def _validate_method(method: str) -> None:
    """Ensure the chosen method is among the supported options."""
    valid_methods = {"range", "floor"} | set(DATE_METHODS.keys())
    if method not in valid_methods:
        raise ValueError(
            f"Unknown method '{method}'. "
            f"Supported methods: {sorted(valid_methods)}"
        )
 
 
# ---------------------------------------------------------------------------
# Specialized Generalization Functions
# ---------------------------------------------------------------------------
 
def generalize_numeric(
    value: Union[int, float],
    step: Optional[Union[int, float]] = None,
    bins: Optional[List[float]] = None,
    method: str = "range",
) -> str:
    """
    Generalize a numeric value into an interval or a floor value.
 
    Args:
        value:  The numeric value to generalize.
        step:   Fixed step size.  e.g. step=10 maps 27 → "20-30" or 20.
        bins:   Custom boundary list. e.g. [0, 18, 65] maps 27 → "18-65".
        method: "range" returns "lower-upper"; "floor" returns the lower bound only.
 
    Returns:
        A string representation of the generalized interval.
 
    Examples:
        >>> generalize_numeric(27, step=10)
        '20-30'
        >>> generalize_numeric(27, bins=[0, 18, 25, 65])
        '25-65'
        >>> generalize_numeric(10, bins=[18, 25, 65])
        '<18'
        >>> generalize_numeric(80, bins=[0, 18, 65])
        '>=65'
    """
    num_val = float(value)
 
    # --- Custom bins ---
    if bins is not None:
        if num_val < bins[0]:
            return f"<{bins[0]}"
        for i in range(len(bins) - 1):
            if bins[i] <= num_val < bins[i + 1]:
                return f"{bins[i]}-{bins[i+1]}"
        return f">={bins[-1]}"
 
    # --- Fixed step ---
    if step is not None:
        lower = int((num_val // step) * step)
        if method == "range":
            return f"{lower}-{lower + int(step)}"
        return str(lower)
 
    return DEFAULT_VALUE
 
 
def generalize_date(value: Any, method: str = "date_year") -> str:
    """
    Generalize a date value by reducing its precision.
 
    Args:
        value:  A datetime object or an ISO-format string (e.g. "2003-06-15").
        method: One of "date_year", "date_month".
 
    Returns:
        A string representation of the generalized date.
 
    Examples:
        >>> generalize_date("2003-06-15", method="date_year")
        '2003'
        >>> generalize_date("2003-06-15", method="date_month")
        '2003-06'
    """
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        return DATE_METHODS[method](dt)
    except (ValueError, TypeError, KeyError):
        return DEFAULT_VALUE
 
 
def generalize_location(value: str, depth: int = 1) -> str:
    """
    Generalize a comma-separated location string by removing the most specific levels.
 
    Args:
        value: A comma-separated location string.
               e.g. "Ouagadougou, Kadiogo, Centre"
        depth: Number of leading (most specific) parts to drop.
               depth=1 → "Kadiogo, Centre"
               depth=2 → "Centre"
 
    Returns:
        A generalized location string, or DEFAULT_VALUE if generalization fails.
 
    Examples:
        >>> generalize_location("Ouagadougou, Kadiogo, Centre", depth=1)
        'Kadiogo, Centre'
        >>> generalize_location("Ouagadougou, Kadiogo, Centre", depth=2)
        'Centre'
    """
    parts = [p.strip() for p in value.split(",")]
    if len(parts) > depth:
        return ", ".join(parts[depth:])
    return DEFAULT_VALUE
 
 
# ---------------------------------------------------------------------------
# Main Router
# ---------------------------------------------------------------------------
 
def apply(
    value: Any,
    step: Optional[Union[int, float]] = None,
    bins: Optional[List[float]] = None,
    depth: int = 1,
    method: str = "range",
    **kwargs,
) -> Optional[str]:
    """
    Apply an advanced generalization strategy to a single value.
 
    The function routes to the appropriate specialist based on the value type
    and the chosen method.
 
    Args:
        value:  The value to generalize. Can be numeric, a date string, a
                datetime object, or a comma-separated location string.
        step:   Fixed step size for numeric generalization (mutually exclusive
                with bins).
        bins:   Custom boundary list for numeric generalization (mutually
                exclusive with step).
        depth:  Number of leading location parts to drop (default: 1).
        method: Generalization strategy. Supported values:
                  - "range"         : numeric interval  e.g. "20-30"
                  - "floor"         : numeric floor      e.g. "20"
                  - "date_year"     : year only          e.g. "2003"
                  - "date_month"    : year + month       e.g. "2003-06"
        **kwargs: Reserved for future extension.
 
    Returns:
        A generalized string, or None if the input is None.
 
    Raises:
        ValueError: If parameters are invalid or in conflict.
 
    Examples:
        >>> apply(None)
        >>> apply(27, step=10)
        '20-30'
        >>> apply(27, bins=[0, 18, 25, 65])
        '25-65'
        >>> apply("2003-06-15", method="date_year")
        '2003'
        >>> apply("Ouagadougou, Kadiogo, Centre", depth=1)
        'Kadiogo, Centre'
    """
    # --- Guard: None passthrough ---
    if value is None:
        return None
 
    # --- Input validation ---
    _validate_step(step)
    _validate_bins(bins)
    _validate_step_bins_conflict(step, bins)
    _validate_depth(depth)
    _validate_method(method)
 
    # --- Route: Date methods ---
    if method in DATE_METHODS:
        return generalize_date(value, method)
 
    # --- Route: Numeric ---
    try:
        float(value)
        return generalize_numeric(value, step=step, bins=bins, method=method)
    except (ValueError, TypeError):
        pass
 
    # --- Route: Location (comma-separated text) ---
    if isinstance(value, str) and "," in value:
        return generalize_location(value, depth=depth)
 
    return DEFAULT_VALUE