import numpy as np

def calculate_psi(baseline_pct: np.ndarray, current_scores: np.ndarray, bins: int = 10) -> float:
    """
    Calculate the Population Stability Index (PSI) between a baseline distribution and a current sample.
    
    Args:
        baseline_pct (np.ndarray): The expected percentages in each bin (from training baseline). Length should equal `bins`.
        current_scores (np.ndarray): The raw model predictions from recent traffic.
        bins (int): Number of bins to use (default 10, over the range [0.0, 1.0]).
        
    Returns:
        float: The calculated PSI value.
        
    Interpretation Thresholds:
        - PSI < 0.1: No significant change in the distribution.
        - 0.1 <= PSI < 0.2: Moderate change — monitor closely.
        - PSI >= 0.2: Significant shift — requires alert and investigation.
    """
    # Ensure baseline is numpy array
    baseline_pct = np.array(baseline_pct)
    
    # Bin the current scores over [0.0, 1.0]
    hist, _ = np.histogram(current_scores, bins=bins, range=(0.0, 1.0))
    
    if len(current_scores) == 0:
        return 0.0 # No data means no drift technically, or undefined. Return 0.
        
    current_pct = hist / len(current_scores)
    
    # Replace zeros with epsilon to avoid division by zero or log(0)
    epsilon = 1e-4
    current_pct = np.where(current_pct == 0, epsilon, current_pct)
    baseline_pct = np.where(baseline_pct == 0, epsilon, baseline_pct)
    
    # Calculate PSI: sum((current% - baseline%) * ln(current% / baseline%))
    psi_values = (current_pct - baseline_pct) * np.log(current_pct / baseline_pct)
    psi = np.sum(psi_values)
    
    return float(psi)
