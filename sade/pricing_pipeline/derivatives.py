"""
Module/File Name: sade/pricing_pipeline/derivatives.py
Date Created / Modified: August 27, 2026
Purpose:
    Provide reference full-history and production active-index derivative fitting.
Executive Overview:
    Preserves causal quadratic mathematics while allowing production to fit only
    the requested active index instead of recomputing historical indices.
Role in SADE:
    First mathematical stage in pricing_pipeline before F4 and RK45.
Inputs:
    Causal timestamp sequence in minutes and close-price history.
Outputs:
    p1 and p2 arrays plus fit-failure count.
Parameters / Configuration:
    Window size and epsilon for derivative-state classification.
Persistent State:
    None.
External Dependencies:
    numpy and Python math.
Main Callers / Consumers:
    PricingPipeline uses causal_quadratic_at_index; tests use both implementations.
Important Assumptions:
    Input timestamps are already source-preserved and causally ordered.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF diagnostics/run_test_009_derivative_analysis.py::causal_quadratic
    - APTF diagnostics/run_test_009_derivative_analysis.py::derivative_state
Scientific Mathematics Changed:
    NO
Computational Scheduling Changed:
    YES
Historical Recomputation Removed:
    YES, from the production Pricing path.
Finding 001 Analytic Projection Changed:
    NO
Explicit Exclusions / What This Module Does NOT Do:
    - No cadence normalization
    - No SDX reads
    - No model fitting beyond causal quadratic derivative extraction
Failure / Error Behavior:
    Numerical fit failures are counted and reflected as NaN output entries.
"""

from __future__ import annotations

import math

import numpy as np


def causal_quadratic(
    times_minutes: np.ndarray,
    prices: np.ndarray,
    window: int = 15,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Compute causal first and second derivatives from close history.

    Purpose:
        Fit a local quadratic over trailing causal window ending at each index and
        derive p1 and p2 from fitted coefficients.
    Arguments / Inputs:
        times_minutes: strictly increasing source timestamps expressed in minutes.
        prices: close price history aligned to times_minutes.
        window: trailing window length used for each local fit.
    Returns / Outputs:
        Tuple (p1, p2, failures), where p1 and p2 are arrays and failures counts
        numerical/degeneracy fit failures.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        times_minutes and prices are same length and causally ordered.
    Failure / Error Behavior:
        Failed fits leave NaN at index and increment failures.
    Scientific Meaning:
        p is close, p1 is first derivative of price vs minute, p2 is second derivative.
    Original APTF Source:
        diagnostics/run_test_009_derivative_analysis.py::causal_quadratic
    Scientific Mathematics Changed:
        NO
    """

    size = len(prices)
    d1 = np.full(size, np.nan)
    d2 = np.full(size, np.nan)
    failures = 0
    for index in range(window - 1, size):
        x = times_minutes[index - window + 1 : index + 1] - times_minutes[index]
        y = prices[index - window + 1 : index + 1]
        design = np.column_stack((x * x, x, np.ones(window)))
        try:
            coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
        except np.linalg.LinAlgError:
            failures += 1
            continue
        if rank != 3 or not np.all(np.isfinite(coefficients)):
            failures += 1
            continue
        d1[index] = coefficients[1]
        d2[index] = 2.0 * coefficients[0]
    return d1, d2, failures


def causal_quadratic_at_index(
    times_minutes: np.ndarray,
    prices: np.ndarray,
    index: int,
    window: int = 15,
) -> tuple[float, float, int]:
    """Compute the existing causal quadratic fit only at one requested index.

    Purpose:
        Remove repeated historical regressions from the live Pricing path.
    Arguments / Inputs:
        Aligned source times and prices, requested active index, and trailing window.
    Returns / Outputs:
        Tuple (p1, p2, failures) for the requested index; unavailable values are NaN.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Arrays are aligned and index identifies the existing causal active row.
    Failure / Error Behavior:
        Insufficient/out-of-range history returns NaN values and zero fit failures;
        numerical/rank/non-finite failure returns NaN values and one failure.
    Scientific Meaning:
        The same local quadratic derivative estimate as causal_quadratic[index].
    Scientific Provenance:
        Existing full-history causal_quadratic implementation.
    Scientific Mathematics Changed:
        NO
    Reference Algorithm:
        causal_quadratic full-history implementation.
    Difference:
        Computes only the requested active index.
    """

    if index < window - 1 or index < 0 or index >= len(prices):
        return math.nan, math.nan, 0
    x = times_minutes[index - window + 1 : index + 1] - times_minutes[index]
    y = prices[index - window + 1 : index + 1]
    design = np.column_stack((x * x, x, np.ones(window)))
    try:
        coefficients, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    except np.linalg.LinAlgError:
        return math.nan, math.nan, 1
    if rank != 3 or not np.all(np.isfinite(coefficients)):
        return math.nan, math.nan, 1
    return float(coefficients[1]), float(2.0 * coefficients[0]), 0


def derivative_state(d1: float, d2: float, epsilon: float) -> str:
    """Classify derivative phase state from p1/p2.

    Purpose:
        Map continuous derivative values into the mature categorical state labels.
    Arguments / Inputs:
        d1: first derivative.
        d2: second derivative.
        epsilon: near-zero threshold for d1.
    Returns / Outputs:
        State label string.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Inputs are from causal_quadratic output.
    Failure / Error Behavior:
        Returns UNAVAILABLE for non-finite values.
    Scientific Meaning:
        Categorical trajectory interpretation over p1/p2.
    Original APTF Source:
        diagnostics/run_test_009_derivative_analysis.py::derivative_state
    Scientific Mathematics Changed:
        NO
    """

    if not math.isfinite(d1) or not math.isfinite(d2):
        return "UNAVAILABLE"
    if abs(d1) <= epsilon:
        return "LOWER_TURNING_REGION" if d2 > 0 else "UPPER_TURNING_REGION" if d2 < 0 else "D2_ZERO"
    if d1 > 0:
        return "RISING_STRENGTHENING" if d2 > 0 else "RISING_WEAKENING" if d2 < 0 else "D2_ZERO"
    return "FALLING_WEAKENING" if d2 > 0 else "FALLING_STRENGTHENING" if d2 < 0 else "D2_ZERO"
