import matplotlib.pyplot as plt
import numpy as np

def plot_distribution(original: list, masked: list, ax=None):
    """
    Plots the probability density histogram.
    Focus: Visualization of the 'Mathematical Blur'.
    """
    if ax is None:
        _, ax = plt.subplots()
    
    ax.hist(original, bins=40, alpha=0.5, label='Original', color='blue', density=True)
    ax.hist(masked, bins=40, alpha=0.5, label='Masked', color='red', density=True)
    ax.set_title("Probability Distribution")
    ax.set_xlabel("Value")
    ax.set_ylabel("Density")
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

def plot_qq_integrity(original: list, masked: list, ax=None):
    """
    Plots the Quantile-Quantile plot.
    Focus: Statistical Integrity validation.
    """
    if ax is None:
        _, ax = plt.subplots()

    percs = np.linspace(0, 100, 100)
    qn_orig = np.percentile(original, percs)
    qn_masked = np.percentile(masked, percs)
    
    ax.plot(qn_orig, qn_masked, ls="", marker="o", color='#1a5f7a', alpha=0.5, label="Data Points")
    
    # Identity line
    lims = [np.min([qn_orig, qn_masked]), np.max([qn_orig, qn_masked])]
    ax.plot(lims, lims, color='#e74c3c', ls="--", label="Perfect Utility Line")
    
    ax.set_title("Q-Q Plot: Masking Quality Analysis")
    ax.set_xlabel("Original Quantiles")
    ax.set_ylabel("Masked Quantiles")
    ax.legend()
    ax.grid(True, alpha=0.2)

def plot_full_report(original: list, masked: list):
    """
    Combines all visual indicators into a single figure.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    plot_distribution(original, masked, ax=ax1)
    plot_qq_integrity(original, masked, ax=ax2)
    
    plt.tight_layout()
    plt.savefig("utility_analysis.png")