from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class Strategy(Protocol):
    """
    Interface (Protocol) that each strategy must adhere to.
    Enables strong typing and simplified extensibility.
    """

    def apply(self, value: Any, **kwargs) -> Any:
        ...