from typing import Any

from maskme.strategies.base import DROP_SENTINEL


def apply(value: Any, **kwargs) -> str:
    """
    Signals that the field must be completely removed from the output.

    The engine interprets the DROP_SENTINEL return value as an instruction
    to delete the field from the record rather than replacing it.

    Args:
        value:    The current field value (ignored).
        **kwargs: Accepted for interface consistency; not used.

    Returns:
        The DROP_SENTINEL string constant.
    """
    return DROP_SENTINEL