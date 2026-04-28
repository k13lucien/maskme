from maskme.strategies.noise import apply as noise_apply
from maskme.analytics.metrics import evaluate_masking
from maskme.analytics.visual import plot_full_report
import numpy as np

# Simulate 1000 salaries (Mean=2500, StdDev=500)
original_salaries = np.random.normal(2500, 500, 1000).tolist()

# Apply deep noise (Sigma=100)
masked_salaries = [noise_apply(s, sigma=100.0, min_val=1200) for s in original_salaries]

# Get Scores
report = evaluate_masking(original_salaries, masked_salaries)

print("=== MASKME PERFORMANCE REPORT ===")
print(f"Efficiency (Individual Protection): {report['efficiency_score']} units")
print(f"Utility (Statistical Integrity): {report['utility_score']} (Target: 1.0)")
print(f"Reliability (Mean Drift): {report['mean_drift']}")

# Show visual proof
#plot_qq_integrity(original_salaries, masked_salaries)
plot_full_report(original_salaries, masked_salaries)