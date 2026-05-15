"""
maskme.utility.metrics._utils
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Shared utilities for the utility metrics layer.

Centralises field-type detection, value extraction, and record alignment
so that field_retention, statistical_fidelity, and information_loss all
operate on consistently prepared data without duplicating logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Field discovery
# ---------------------------------------------------------------------------

def all_fields(records: List[Dict[str, Any]]) -> List[str]:
    """
    Return the union of all field names found across records, preserving
    insertion order from the first record as the primary ordering.

    Args:
        records: List of record dicts.

    Returns:
        Ordered list of unique field names.
    """
    seen: Dict[str, None] = {}
    for record in records:
        for key in record:
            seen[key] = None
    return list(seen)


def is_numerical(values: List[str]) -> bool:
    """
    Return True if all non-empty string values can be cast to float.

    Used to auto-detect numerical fields when the caller does not
    explicitly provide numerical_fields / categorical_fields.

    Args:
        values: List of string values sampled from a field.

    Returns:
        True if the field is numerical, False otherwise.
    """
    for v in values:
        if v == "" or v is None:
            continue
        try:
            float(v)
        except (ValueError, TypeError):
            return False
    return True


def classify_fields(
    original: List[Dict[str, Any]],
    numerical_fields: Optional[List[str]] = None,
    categorical_fields: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """
    Resolve numerical and categorical field lists.

    If both are provided explicitly, they are returned as-is.
    If only one is provided, the other is inferred from the remaining
    fields in the dataset.
    If neither is provided, all fields are auto-classified by attempting
    float conversion on each field's values.

    Args:
        original:           The original dataset.
        numerical_fields:   Explicitly declared numerical field names.
        categorical_fields: Explicitly declared categorical field names.

    Returns:
        (numerical_fields, categorical_fields) — both lists, no overlap.
    """
    fields = all_fields(original)

    if numerical_fields is not None and categorical_fields is not None:
        return numerical_fields, categorical_fields

    if numerical_fields is not None:
        num_set  = set(numerical_fields)
        cat      = [f for f in fields if f not in num_set]
        return numerical_fields, cat

    if categorical_fields is not None:
        cat_set  = set(categorical_fields)
        num      = [f for f in fields if f not in cat_set]
        return num, categorical_fields

    # Auto-classify: sample first record to check float convertibility
    num, cat = [], []
    for f in fields:
        sample = [str(r.get(f, "")) for r in original[:50] if f in r]
        if sample and is_numerical(sample):
            num.append(f)
        else:
            cat.append(f)

    return num, cat


# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------

def field_values(
    records: List[Dict[str, Any]],
    field: str,
) -> List[Optional[str]]:
    """
    Extract values for a given field from all records.

    Missing keys are returned as None (distinct from an empty string,
    which signals a field that was cleared rather than dropped).

    Args:
        records: List of record dicts.
        field:   Field name to extract.

    Returns:
        List of string values or None for missing keys.
    """
    return [
        str(r[field]) if field in r else None
        for r in records
    ]


def paired_values(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
    field: str,
) -> List[Tuple[Optional[str], Optional[str]]]:
    """
    Return (original_value, anonymised_value) pairs for a field,
    aligned by record index.

    Assumes original and anonymised have the same number of records
    in the same order (as produced by MaskMe.mask()).

    Args:
        original:   Original dataset.
        anonymised: Anonymised dataset.
        field:      Field name.

    Returns:
        List of (orig_val, anon_val) tuples, None for missing keys.
    """
    orig_vals = field_values(original, field)
    anon_vals = field_values(anonymised, field)
    return list(zip(orig_vals, anon_vals))


# ---------------------------------------------------------------------------
# Record alignment validation
# ---------------------------------------------------------------------------

def validate_alignment(
    original: List[Dict[str, Any]],
    anonymised: List[Dict[str, Any]],
) -> None:
    """
    Verify that original and anonymised datasets have the same length.

    MaskMe.mask() produces one output record per input record in the same
    order, so length equality is a necessary condition for paired analysis.

    Args:
        original:   Original dataset.
        anonymised: Anonymised dataset.

    Raises:
        ValueError: If lengths differ.
    """
    if len(original) != len(anonymised):
        raise ValueError(
            f"Original and anonymised datasets must have the same number of "
            f"records. Got {len(original)} vs {len(anonymised)}."
        )


# ---------------------------------------------------------------------------
# Value comparison helpers
# ---------------------------------------------------------------------------

def value_changed(orig: Optional[str], anon: Optional[str]) -> bool:
    """
    Return True if the anonymised value differs from the original.

    A value is considered changed if:
      - The key was present in original but absent in anonymised (dropped).
      - The string representation of the value changed.

    Args:
        orig: Original value (None if key was absent in original).
        anon: Anonymised value (None if key was dropped).

    Returns:
        True if the value changed or was dropped.
    """
    return orig != anon


def value_dropped(orig: Optional[str], anon: Optional[str]) -> bool:
    """
    Return True if the field was present in original but dropped in anonymised.

    Args:
        orig: Original value (None if key was absent).
        anon: Anonymised value (None if key was dropped).
    """
    return orig is not None and anon is None


def safe_float(value: Optional[str]) -> Optional[float]:
    """
    Attempt to convert a string to float. Return None on failure.

    Args:
        value: String value or None.

    Returns:
        float or None.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None