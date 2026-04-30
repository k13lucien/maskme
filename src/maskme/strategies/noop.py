def apply(value, **kwargs):
    """
    Explicitly returns the value as-is.
    Useful for documenting fields that must remain untouched.
    """
    return value