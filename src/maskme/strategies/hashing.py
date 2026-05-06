import hashlib
import warnings
from typing import Any

_DEFAULT_ALGO = "sha256"


def apply(value: Any, salt: str = "", algo: str = _DEFAULT_ALGO, **kwargs) -> str:
    """
    Transform a value into a hex digest using a specified hashing algorithm.

    The value and salt are concatenated before hashing. If the requested
    algorithm is unavailable, a warning is emitted and sha256 is used as
    a fallback.

    Args:
        value:    The input value to hash. Returns "" if None.
        salt:     An optional string appended to the value before hashing.
        algo:     The hashing algorithm to use (e.g. "sha256", "sha512",
                  "blake2b"). Must be supported by hashlib. Defaults to
                  "sha256".
        **kwargs: Accepted for interface consistency; not used.

    Returns:
        The hexadecimal digest of the hashed value, or "" if value is None.

    Raises:
        No exception is raised for unsupported algorithms — a warning is
        emitted and sha256 is used instead.
    """
    if value is None:
        return ""

    prepared = f"{value}{salt}".encode("utf-8")

    try:
        hash_obj = hashlib.new(algo, prepared)
    except ValueError:
        warnings.warn(
            f"Unsupported hash algorithm '{algo}'. Falling back to sha256.",
            stacklevel=2,
        )
        hash_obj = hashlib.new(_DEFAULT_ALGO, prepared)

    return hash_obj.hexdigest()