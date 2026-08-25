"""
Module/File Name: sade/pricing_pipeline/derivatives.py
Date Created / Migrated: August 25, 2026
Purpose:
    Provide causal derivative mathematics used by SADE pricing pipeline.
Executive Overview:
    Implements causal quadratic local fitting to produce p1 and p2 from close
    history and derivative-state classification helpers.
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
    sade.pricing_pipeline.pipeline and tests.
Important Assumptions:
    Input timestamps are already source-preserved and causally ordered.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF diagnostics/run_test_009_derivative_analysis.py::causal_quadratic
    - APTF diagnostics/run_test_009_derivative_analysis.py::derivative_state
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
