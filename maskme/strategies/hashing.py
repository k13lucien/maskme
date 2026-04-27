import hashlib
from typing import Any

def apply(value: Any, salt: str = "", **kwargs) -> str:
    """
    Transforms a value into a SHA-256 hash string.

    Args:
        value (Any): The input value to be hashed.
        salt (str): An optional string appended to the value before hashing 
                    to increase security. Defaults to an empty string.
        **kwargs: Additional arguments (ignored for this strategy).

    Returns:
        str: The hexadecimal representation of the SHA-256 hash. 
             Returns an empty string or handles None if the value is missing.
    """
    if value is None:
        return ""
    
    prepared_string = f"{value}{salt}".encode('utf-8')
    
    return hashlib.sha256(prepared_string).hexdigest()