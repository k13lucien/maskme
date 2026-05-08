"""
maskme.io.base
~~~~~~~~~~~~~~
Formal contract for all I/O format handlers.

Any class that implements read() and write() with the correct signatures
is automatically considered a valid FormatHandler — no explicit inheritance
needed (structural subtyping via Protocol).

Adding a new format:
    1. Create a new file  io/<format>_handler.py
    2. Implement a class that satisfies FormatHandler
    3. Register it in io/__init__.py under IO_HANDLERS
"""

from typing import Any, Dict, Iterable, Protocol, runtime_checkable


@runtime_checkable
class FormatHandler(Protocol):
    """
    Protocol that every I/O handler must satisfy.

    Handlers are responsible for:
    - Reading a stream and yielding records as dicts (read)
    - Writing an iterable of dicts to a stream (write)

    Streams can be file objects, sys.stdin, sys.stdout, or any
    object that supports read()/write() operations.
    """

    def read(self, stream: Any) -> Iterable[Dict]:
        """
        Read records from a stream and yield them as dicts.

        Implementations should prefer lazy/streaming reads over
        loading the entire source into memory where the format allows.

        Args:
            stream: A readable file-like object.

        Yields:
            One dict per record.
        """
        ...

    def write(self, records: Iterable[Dict], stream: Any) -> None:
        """
        Write an iterable of dicts to a stream.

        Implementations should consume records lazily where possible
        to preserve the memory efficiency of the upstream generator.

        Args:
            records: An iterable of dicts to write.
            stream:  A writable file-like object.
        """
        ...