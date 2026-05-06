from typing import Any


def _validate_char(char: str) -> None:
    """Ensure char is exactly one character."""
    if len(char) != 1:
        raise ValueError(
            f"'char' must be a single character, got: {char!r} ({len(char)} chars)"
        )


def _validate_keep(keep_start: int, keep_end: int) -> None:
    """Ensure keep_start and keep_end are non-negative integers."""
    if not isinstance(keep_start, int) or keep_start < 0:
        raise ValueError(
            f"'keep_start' must be a non-negative integer, got: {keep_start!r}"
        )
    if not isinstance(keep_end, int) or keep_end < 0:
        raise ValueError(
            f"'keep_end' must be a non-negative integer, got: {keep_end!r}"
        )


def apply(
    value: Any,
    char: str = "*",
    keep_start: int = 0,
    keep_end: int = 0,
    **kwargs,
) -> str:
    """
    Redact a value by replacing its characters with a placeholder.

    The original string length is always preserved. Characters outside
    the visible windows are replaced by ``char``.

    Args:
        value:      The value to redact. Converted to str before processing.
        char:       The single character used for redaction (default: "*").
                    Must be exactly one character.
        keep_start: Number of characters to keep visible at the beginning.
                    Must be a non-negative integer.
        keep_end:   Number of characters to keep visible at the end.
                    Must be a non-negative integer.
        **kwargs:   Accepted for interface consistency; not used.

    Returns:
        The redacted string, always the same length as str(value).

    Raises:
        ValueError: If char is not exactly one character, or if keep_start
                    or keep_end are not non-negative integers.
    """
    if value is None:
        return ""

    _validate_char(char)
    _validate_keep(keep_start, keep_end)

    str_val = str(value)
    length = len(str_val)

    if length <= keep_start + keep_end:
        return char * length

    visible_start = str_val[:keep_start]
    visible_end = str_val[length - keep_end:] if keep_end > 0 else ""
    redacted_part = char * (length - keep_start - keep_end)

    return f"{visible_start}{redacted_part}{visible_end}"