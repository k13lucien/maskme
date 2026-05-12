"""
maskme.analytics.metrics._utils
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Shared utilities for the analytics metrics layer.

Centralises equivalence-class construction so that k-anonymity,
l-diversity and t-closeness all operate on identically built groups
without duplicating logic.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple


def build_equivalence_classes(
    records: List[Dict[str, Any]],
    quasi_identifiers: List[str],
) -> Dict[Tuple, List[Dict[str, Any]]]:
    """
    Group records into equivalence classes by their quasi-identifier values.

    Two records belong to the same equivalence class when they share
    identical values for every quasi-identifier field.  Missing fields
    are treated as the empty string so that absent values still group
    consistently.

    Args:
        records:           List of record dicts.
        quasi_identifiers: Ordered list of field names that form the
                           quasi-identifier (e.g. ["age", "zip", "gender"]).

    Returns:
        A dict mapping QI-value tuples to lists of matching records.
        Keys are stable, ordered tuples aligned to quasi_identifiers.

    Example:
        >>> records = [
        ...     {"age": "30", "zip": "75001", "salary": "50000"},
        ...     {"age": "30", "zip": "75001", "salary": "60000"},
        ... ]
        >>> classes = build_equivalence_classes(records, ["age", "zip"])
        >>> len(classes)
        1
    """
    classes: Dict[Tuple, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = tuple(str(record.get(qi, "")) for qi in quasi_identifiers)
        classes[key].append(record)
    return dict(classes)