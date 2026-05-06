from typing import Any


def apply(value: Any, **kwargs) -> Any:
    """
    Return the value as-is without any transformation.

    Useful for explicitly documenting fields that must remain untouched,
    making anonymization intent visible in the rule set rather than
    relying on the absence of a rule.

    Args:
        value:    The value to pass through unchanged.
        **kwargs: Accepted for interface consistency; not used.

    Returns:
        The original value, unmodified.
    """
    return value