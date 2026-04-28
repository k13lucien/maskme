import random
import hashlib
from typing import Any, Union, Optional

def apply(
    value: Any, 
    sigma: float = 1.0, 
    min_val: Optional[float] = None, 
    max_val: Optional[float] = None,
    precision: Optional[int] = None,
    seed: Optional[Any] = None,
    **kwargs
) -> Union[float, int, Any]:
    """
    Advanced Gaussian Noise implementation for Differential Privacy.
    """
    if value is None:
        return None
        
    try:
        original_value = float(value)
        
        # Deterministic noise: same seed + same value = same noise
        if seed is not None:
            # Create a unique integer from the seed to fix the random state
            combined_seed = f"{seed}_{sigma}"
            gen_seed = int(hashlib.sha256(combined_seed.encode()).hexdigest(), 16)
            random.seed(gen_seed)

        # Mathematical core: Gaussian distribution N(0, sigma^2)
        noise = random.gauss(0, sigma)
        masked_value = original_value + noise
        
        # Business constraints (Clipping)
        if min_val is not None:
            masked_value = max(min_val, masked_value)
        if max_val is not None:
            masked_value = min(max_val, masked_value)
            
        # Data Utility: Type and precision management
        if precision is not None:
            masked_value = round(masked_value, precision)
            return int(masked_value) if precision == 0 else masked_value
            
        return masked_value
        
    except (ValueError, TypeError):
        return value
    finally:
        if seed is not None:
            random.seed() # Reset random state