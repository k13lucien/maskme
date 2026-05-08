"""
maskme.io
~~~~~~~~~
Central registry and factory for I/O format handlers.

To add a new format:
    1. Create io/<format>_handler.py implementing FormatHandler
    2. Import the class below and add it to IO_HANDLERS
"""

from maskme.io.base import FormatHandler
from maskme.io.csv_handler import CSVHandler
from maskme.io.json_handler import JSONHandler
from maskme.io.jsonl_handler import JSONLHandler

IO_HANDLERS: dict[str, type[FormatHandler]] = {
    "csv":  CSVHandler,
    "json": JSONHandler,
    "jsonl": JSONLHandler,
}


def get_handler(format_name: str) -> FormatHandler:
    """
    Factory: return a handler instance for the given format name.

    Args:
        format_name: Case-insensitive format key (e.g. "csv", "jsonl").

    Returns:
        An instance of the matching FormatHandler.

    Raises:
        ValueError: If the format is not registered in IO_HANDLERS.
    """
    handler_class = IO_HANDLERS.get(format_name.lower())

    if handler_class is None:
        supported = ", ".join(sorted(IO_HANDLERS.keys()))
        raise ValueError(
            f"Unsupported format: '{format_name}'. "
            f"Supported formats: {supported}"
        )

    return handler_class()