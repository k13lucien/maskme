from typing import Any, Optional

def apply(value: Any, char: str = "*", keep_start: int = 0, keep_end: int = 0, **kwargs) -> str:
    """
    Redacts a string value by replacing characters with a placeholder.
    
    Args:
        value: The value to redact.
        char: The character to use for redaction (default: '*').
        keep_start: Number of characters to keep visible at the beginning.
        keep_end: Number of characters to keep visible at the end.
    """
    str_val = str(value)
    length = len(str_val)
    
    if length <= keep_start + keep_end:
        return char * length
        
    visible_start = str_val[:keep_start]
    visible_end = str_val[length - keep_end:] if keep_end > 0 else ""
    
    redacted_part = char * (length - keep_start - keep_end)
    
    return f"{visible_start}{redacted_part}{visible_end}"