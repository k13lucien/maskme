from typing import Any, Callable

# ---------------------------------------------------------------------------
# Strategy function type alias
# ---------------------------------------------------------------------------

# All strategies are plain functions matching this signature.
# The engine calls: apply(value, salt=..., **extra_params)
StrategyFn = Callable[..., Any]

# Returned by a strategy to signal that the field must be removed entirely.
DROP_SENTINEL = "__DROP__"