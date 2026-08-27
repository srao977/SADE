"""
Module/File Name: sade/pricing_pipeline/dynamics.py
Date Created / Modified: August 27, 2026
Purpose:
    Provide reference full-history and production active-index F4 fitting.
Executive Overview:
    Preserves the standardized ridge model while allowing production to fit only
    the requested active index instead of recomputing historical indices.
Role in SADE:
    Middle mathematical stage between derivative extraction and RK45 projection.
Inputs:
    p, p1, p2, and jp arrays.
Outputs:
    Fit matrices and per-index local dynamics coefficients.
Parameters / Configuration:
    Window length and ridge lambda.
Persistent State:
    None.
External Dependencies:
    numpy.
Main Callers / Consumers:
    PricingPipeline uses fit_f4_at_index; equivalence tests use both implementations.
Important Assumptions:
    jp represents causal p2 differences on observed history.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF diagnostics/run_test_013b_qqq_validation.py::allocate_fit
    - APTF diagnostics/run_test_013b_qqq_validation.py::fit_f4
    - APTF diagnostics/run_test_013b_qqq_validation.py::valid_fit
Scientific Mathematics Changed:
    NO
Standard Deviation:
    POPULATION
ddof:
    0
Normal Equations:
    PRESERVED
Condition Number:
    SCIENTIFICALLY DOWNSTREAM-RELEVANT
Go Migration:
    NOT IMPLEMENTED
Computational Scheduling Changed:
    YES
Historical Recomputation Removed:
    YES, from the production Pricing path.
Finding 001 Analytic Projection Changed:
    NO
Explicit Exclusions / What This Module Does NOT Do:
    - No RK45 integration
    - No policy emission logic
Failure / Error Behavior:
    Ill-conditioned or invalid fits remain NaN for that index.
"""

from __future__ import annotations

import numpy as np


def allocate_fit(size: int, coefficient_count: int) -> dict[str, np.ndarray]:
    """Allocate fit arrays for all observation indices."""

    return {
        "standardized": np.full((size, coefficient_count), np.nan),
        "physical": np.full((size, 4), np.nan),
        "means": np.full((size, 3), np.nan),
        "scales": np.full((size, 3), np.nan),
        "minimum": np.full((size, 3), np.nan),
        "maximum": np.full((size, 3), np.nan),
        "condition": np.full(size, np.nan),
    }


def fit_f4(
    p: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
    jp: np.ndarray,
    window: int,
    ridge_lambda: float = 1.0,
) -> dict[str, np.ndarray]:
    """Fit F4 local dynamics over causal trailing windows.

    Purpose:
        Fit ridge-regularized standardized linear model for jerk target jp.
    Arguments / Inputs:
        p, p1, p2, jp arrays; window size; ridge_lambda.
    Returns / Outputs:
        Fit dictionary containing standardized coefficients and physical form.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Input arrays are aligned and causal.
    Failure / Error Behavior:
        Unfit indices remain NaN and are excluded by valid_fit checks.
    Scientific Meaning:
        Produces local affine dynamics used by RK45 step integration.
    Original APTF Source:
        diagnostics/run_test_013b_qqq_validation.py::fit_f4
    Scientific Mathematics Changed:
        NO
    """

    result = allocate_fit(len(p), 4)
    ridge = np.diag([0.0, 1.0, 1.0, 1.0])
    for index in range(window, len(p) - 1):
        ids = np.arange(index - window + 1, index + 1)
        if not np.all(np.isfinite(jp[ids])):
            continue
        values = np.column_stack((p[ids], p1[ids], p2[ids]))
        means = values.mean(axis=0)
        scales = values.std(axis=0, ddof=0)
        if np.any(scales <= 0) or not np.all(np.isfinite(scales)):
            continue
        design = np.column_stack((np.ones(window), (values - means) / scales))
        try:
            beta = np.linalg.solve(design.T @ design + ridge_lambda * ridge, design.T @ jp[ids])
        except np.linalg.LinAlgError:
            continue
        slopes = beta[1:] / scales
        result["standardized"][index] = beta
        result["physical"][index] = np.r_[beta[0] - slopes @ means, slopes]
        result["means"][index] = means
        result["scales"][index] = scales
        result["minimum"][index] = values.min(axis=0)
        result["maximum"][index] = values.max(axis=0)
        result["condition"][index] = np.linalg.cond(design)
    return result


def fit_f4_at_index(
    p: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
    jp: np.ndarray,
    index: int,
    window: int,
    ridge_lambda: float = 1.0,
) -> dict[str, np.ndarray | float] | None:
    """Fit the existing F4 model only at one requested index.

    Purpose:
        Remove repeated historical F4 solves from the live Pricing path.
    Arguments / Inputs:
        Aligned p, p1, p2, jp arrays; requested active index; fit settings.
    Returns / Outputs:
        One fit row, or None when the reference implementation would leave it NaN.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Input arrays are aligned and causal.
    Failure / Error Behavior:
        Invalid history, scales, or solve returns None.
    Scientific Meaning:
        The same local affine dynamics as fit_f4 at the requested index.
    Scientific Provenance:
        Existing full-history fit_f4 implementation.
    Scientific Mathematics Changed:
        NO
    Reference Algorithm:
        fit_f4 full-history implementation.
    Difference:
        Computes only the requested active index.
    """

    if index < window - 1 or index < 0 or index >= len(p) - 1:
        return None
    ids = np.arange(index - window + 1, index + 1)
    if not np.all(np.isfinite(jp[ids])):
        return None
    values = np.column_stack((p[ids], p1[ids], p2[ids]))
    means = values.mean(axis=0)
    scales = values.std(axis=0, ddof=0)
    if np.any(scales <= 0) or not np.all(np.isfinite(scales)):
        return None
    design = np.column_stack((np.ones(window), (values - means) / scales))
    ridge = np.diag([0.0, 1.0, 1.0, 1.0])
    try:
        beta = np.linalg.solve(design.T @ design + ridge_lambda * ridge, design.T @ jp[ids])
    except np.linalg.LinAlgError:
        return None
    slopes = beta[1:] / scales
    return {
        "standardized": beta,
        "physical": np.r_[beta[0] - slopes @ means, slopes],
        "means": means,
        "scales": scales,
        "minimum": values.min(axis=0),
        "maximum": values.max(axis=0),
        "condition": float(np.linalg.cond(design)),
    }


def valid_fit(fit: dict[str, np.ndarray], index: int) -> bool:
    """Return True when standardized coefficients are finite at index."""

    return bool(np.all(np.isfinite(fit["standardized"][index])))
