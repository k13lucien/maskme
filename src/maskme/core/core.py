import copy
from maskme.strategies import STRATEGIES
from typing import Any, Dict, List, Union
from concurrent.futures import ProcessPoolExecutor

class MaskMe:
    """
    Main engine for agnostic data anonymization.
    
    This class handles the traversal of nested dictionaries and applies
    specified anonymization strategies based on a provided rule set.
    """

    def __init__(self, rules: Dict[str, str], salt: str = ""):
        """
        Initializes the MaskMe engine with rules and a global salt.

        Args:
            rules (Dict[str, str]): A dictionary mapping data paths (e.g., 'user.email') 
                                    to strategy names.
            salt (str): A global salt used for cryptographic operations like hashing.
        """
        self.rules = rules
        self.salt = salt
        self.strategies = STRATEGIES

    def _get_nested(self, data: Dict, path: str) -> Any:
        """
        Retrieves a value from a nested dictionary using dot notation.

        Args:
            data (Dict): The dictionary to search.
            path (str): The dot-separated path (e.g., 'identity.name').

        Returns:
            Any: The value found at the path, or None if the path does not exist.
        """
        keys = path.split('.')
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data

    def _set_nested(self, data: Dict, path: str, value: Any):
        """
        Sets a value in a nested dictionary using dot notation, creating keys if needed.

        Args:
            data (Dict): The dictionary to modify.
            path (str): The dot-separated path where the value should be set.
            value (Any): The new value to assign at the specified path.
        """
        keys = path.split('.')
        for key in keys[:-1]:
            data = data.setdefault(key, {})
        data[keys[-1]] = value
    
    def _delete_nested(self, data: Dict, path: str):
        """Deletes a key in a nested dictionary via its path."""
        parts = path.split(".")
        for part in parts[:-1]:
            data = data.get(part, {})
        
        if parts[-1] in data:
            del data[parts[-1]]

    def mask(self, data_iterator):
        """
        Anonymizes data record by record to save memory.
        
        Args:
            data_iterator (Iterable[Dict]): A generator or list of records.
            
        Yields:
            Dict: The next anonymized record.
        """
        for record in data_iterator:
            yield self._process_record(copy.deepcopy(record))

    # TODO: Add method for parallel processing using multiprocessing futures for large datasets.

    def _process_record(self, record: Dict) -> Dict:
        """
        Applies anonymization rules to a single record with support for 
        parameterized strategies.

        Args:
            record (Dict): A single data record (dictionary).

        Returns:
            Dict: The processed record with anonymized fields.
        """
        for path, config in self.rules.items():
            # Determine if config is a simple string or a dictionary with params
            if isinstance(config, dict):
                strategy_name = config.get("strategy")
                params = {k: v for k, v in config.items() if k != "strategy"}
            else:
                strategy_name = config
                params = {}

            current_val = self._get_nested(record, path)
            
            if current_val is not None and strategy_name in STRATEGIES:

                strategy_func = self.strategies[strategy_name]
                
                new_value = strategy_func(
                    current_val, 
                    salt=self.salt, 
                    **params
                )
                
                if new_value == "__DROP__":
                    self._delete_nested(record, path)
                else:
                    self._set_nested(record, path, new_value)
                
        return record