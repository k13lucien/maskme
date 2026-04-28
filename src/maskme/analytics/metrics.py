import numpy as np

def evaluate_masking(original: list, masked: list) -> dict:
    """
    Calculates key performance indicators for the masking process.
    """
    orig = np.array(original)
    mask = np.array(masked)
    
    # 1. Efficiency (Protection): Mean Absolute Error
    # Higher means the individual is better 'hidden' in the noise.
    efficiency = np.mean(np.abs(orig - mask))
    
    # 2. Utility (Data Quality): Variance Preservation Ratio
    # Aim for 1.0. Measures if the statistical 'spread' is maintained.
    utility = np.var(mask) / np.var(orig)
    
    # 3. Reliability: Mean Drift
    # Measures the shift in the global average. Should be close to 0.
    drift = np.abs(np.mean(orig) - np.mean(mask))
    
    return {
        "efficiency_score": round(efficiency, 4),
        "utility_score": round(utility, 4),
        "mean_drift": round(drift, 4)
    }