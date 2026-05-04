"""
maskme.engine
~~~~~~~~~~~~~
Primary engine of anonymization. Orchestrates rule traversal,
strategy resolution, and the application of transformations.
"""

import copy
import inspect
import logging
import warnings
from typing import Any, Dict, Generator, Iterable

from maskme.core._sentinel import _MISSING
from maskme.core.navigation import delete_nested, get_nested, set_nested
from maskme.strategies import STRATEGIES

logger = logging.getLogger(__name__)


class MaskMe:
    """
    Agnostic data anonymization engine

    Scans nested dictionaries and applies anonymization strategies
    defined by a set of rules.
    """

    def __init__(self, rules: Dict[str, Any], salt: str = ""):
        """
        Args:
            rules: Dictionary associating paths (e.g., 'user.email') with 
            a simple (str) or parameterized strategy 
            (e.g., {"strategy": "mask", "char": "*"}).
            
            salt: Global salt for cryptographic strategies.
        """
        self.rules = rules
        self.salt = salt
        self.strategies: Dict[str, Any] = dict(STRATEGIES)

    def mask(
        self, data_iterator: Iterable[Dict]
    ) -> Generator[Dict, None, None]:
        """
        Anonymizes records one by one to conserve memory.

        Args:
            data_iterator: Dictionary generator or list.

        Yields:
            The next anonymized record.
        """
        for record in data_iterator:
            yield self._process_record(copy.deepcopy(record))

    def _process_record(self, record: Dict) -> Dict:
        """
        Applies anonymization rules to a single record.

        Args:
            record: A record (dict) to anonymize.

        Returns:
            The modified record with the anonymized fields.
        """
        for path, config in self.rules.items():
            strategy_name, params = self._resolve_config(config)

            if not self._validate_strategy(strategy_name, path):
                continue

            current_val = get_nested(record, path)
            if current_val is _MISSING:
                continue

            new_value = self._apply_strategy(strategy_name, current_val, params)

            if new_value == "__DROP__":
                delete_nested(record, path)
            else:
                set_nested(record, path, new_value)

        return record

    def _resolve_config(self, config: Any) -> tuple[str, Dict]:
        """Extracts the strategy name and parameters from the configuration."""
        if isinstance(config, dict):
            strategy_name = config.get("strategy", "")
            params = {k: v for k, v in config.items() if k != "strategy"}
        else:
            strategy_name = config
            params = {}
        return strategy_name, params

    def _validate_strategy(self, strategy_name: str, path: str) -> bool:
        """
        Checks if a strategy is known. Emits a warning otherwise.

        Returns:
            True if the strategy is valid, False otherwise.
        """
        if strategy_name not in self.strategies:
            warnings.warn(
                f"Unknown strategy '{strategy_name}' for path "
                f"'{path}'. The field will not be anonymized.",
                stacklevel=3,
            )
            logger.warning(
                "Unknown strategy '%s' for path '%s'.", strategy_name, path
            )
            return False
        return True

    def _apply_strategy(
        self, strategy_name: str, value: Any, params: Dict
    ) -> Any:
        """
        Calls the strategy function with conditional salt injection.

        The salt is only injected if the strategy declares this parameter,
        to not impose an implicit contract on all functions.

        Args:
            strategy_name: Name of the strategy to apply.
            value:         Current value of the field.
            params:        Additional parameters from the configuration.

        Returns:
            The transformed value (or "__DROP__" to remove the field).
        """
        strategy_func = self.strategies[strategy_name]
        sig = inspect.signature(strategy_func)
        extra = {"salt": self.salt} if "salt" in sig.parameters else {}
        return strategy_func(value, **extra, **params)