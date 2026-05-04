"""
maskme.navigation
~~~~~~~~~~~~~~~~~
Pure functions for traversing nested dictionaries using dot notation.

They are stateless and have no side effects (except for `delete_nested`,
which modifies the dictionary passed as an argument). 
"""

from typing import Any, Dict

from maskme.core._sentinel import _MISSING


def get_nested(data: Dict, path: str) -> Any:
    """
    Retrieves a value from a nested dictionary via a point-separated path.

    Args:
        data: The source dictionary.
        path: The path (e.g., 'user.address.city').

    Returns:
        The retrieved value, or the sentinel _MISSING if the path is missing.
        This allows the caller to distinguish a missing key from an explicitly None value.
    """
    keys = path.split(".")
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return _MISSING
        data = data[key]
    return data


def set_nested(data: Dict, path: str, value: Any) -> None:
    """
    Assigns a value to a nested dictionary, creating any missing intermediate keys if necessary.

    Args:
        data: The dictionary to modify.
        path: The point-separated path to the destination.
        value: The value to assign.
    """
    keys = path.split(".")
    for key in keys[:-1]:
        data = data.setdefault(key, {})
    data[keys[-1]] = value


def delete_nested(data: Dict, path: str) -> None:
    """
    Deletes a key from a nested dictionary using a point-separated path.

    Aborts cleanly (without exception) if:
    - the path or an intermediate node is missing,
    - an intermediate node is not a dictionary,
    - the terminal key does not exist.

    Args:
        data: The dictionary to modify.
        path: The point-separated path to the key to delete.
    """
    parts = path.split(".")

    for part in parts[:-1]:
        if not isinstance(data, dict) or part not in data:
            return
        data = data[part]

    if isinstance(data, dict):
        data.pop(parts[-1], None)