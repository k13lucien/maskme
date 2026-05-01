from .csv_handler import CSVHandler
from .json_handler import JSONHandler
from .jsonl_handler import JSONLHandler

# Central Registry for I/O Handlers
IO_HANDLERS = {
    "csv": CSVHandler,
    "json": JSONHandler,
    "jsonl": JSONLHandler
}

def get_handler(format_name: str):
    """
    Factory to retrieve a handler instance by its format name.
    """
    handler_class = IO_HANDLERS.get(format_name.lower())
    if not handler_class:
        raise ValueError(f"Unsupported format: {format_name}")
    return handler_class()