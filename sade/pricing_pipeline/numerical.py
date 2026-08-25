"""
Module/File Name: sade/pricing_pipeline/numerical.py
Date Created / Migrated: August 25, 2026
Purpose:
    Assemble PriceEngine numerical payload from fitted/projection state.
Executive Overview:
    Converts local model and RK45 outputs into the field-complete numerical
    dictionary required by PriceEngine policy.
Role in SADE:
    Final mathematical assembly stage before PriceEngine.observe.
Inputs:
    Observation metadata, p/p1/p2 arrays, fit outputs, and solve_cover outputs.
Outputs:
    Numerical dictionary consumed by PriceEngine.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    numpy and scipy.linalg.expm.
Main Callers / Consumers:
    sade.pricing_pipeline.pipeline and equivalence tests.
Important Assumptions:
    Inputs are aligned and observation index is valid.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF diagnostics/run_test_014_policy_development.py::build_numerical
Explicit Exclusions / What This Module Does NOT Do:
    - No policy classification
    - No source-stream reads
Failure / Error Behavior:
    Caller is responsible for index validity and required keys.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from scipy.linalg import expm


def build_numerical_row(
    index: int,
    entity: str,
    timestamp: str,
    session: str,
    open_value: float,
    high_value: float,
    low_value: float,
    close_value: float,
    volume_value: float,
    source_provider: str,
    fit: dict[str, np.ndarray],
    solved: dict[int, dict[str, object]],
    failed: dict[int, str],
    p: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
) -> dict[str, Any]:
    """Build one numerical payload row for PriceEngine.observe.

    Purpose:
        Materialize all required PriceEngine numerical fields with stable semantics.
    Arguments / Inputs:
        Current index metadata, fit map, solved/failed maps, p/p1/p2 arrays.
    Returns / Outputs:
        Numerical dictionary containing projected values and stability metrics.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        fit contains finite model entries for index.
    Failure / Error Behavior:
        Raises index/key errors if required data is absent.
    Scientific Meaning:
        Preserves mature numerical assembly contract for PriceEngine policy.
    Original APTF Source:
        diagnostics/run_test_014_policy_development.py::build_numerical
    Scientific Mathematics Changed:
        NO
    """

    physical = fit["physical"][index]
    matrix = np.asarray([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], physical[1:]])
    eigenvalues = np.linalg.eigvals(matrix)
    amplification = float(max(np.linalg.norm(expm(matrix)[:, component]) for component in range(3)))

    if index in failed:
        projected = np.asarray([p[index], p1[index], p2[index]])
        success = False
        domain_exit = False
    else:
        projected = np.asarray(solved[index]["trajectory"])[-1]
        success = True
        domain_exit = bool(solved[index]["envelope_exit"])

    return {
        "index": index,
        "observation_index": index + 1,
        "symbol": entity,
        "timestamp": timestamp,
        "session": session,
        "open": open_value,
        "high": high_value,
        "low": low_value,
        "close": close_value,
        "volume": volume_value,
        "source_provider": source_provider,
        "p": p[index],
        "p1": p1[index],
        "p2": p2[index],
        "projected_p": projected[0],
        "projected_p1": projected[1],
        "projected_p2": projected[2],
        "rk_success": success,
        "domain_exit": domain_exit,
        "condition_number": fit["condition"][index],
        "max_real_eigenvalue": float(eigenvalues.real.max()),
        "perturbation_amplification": amplification,
        "local_coefficients_json": json.dumps(fit["standardized"][index].tolist(), separators=(",", ":")),
        "local_center_json": json.dumps(fit["means"][index].tolist(), separators=(",", ":")),
        "local_scale_json": json.dumps(fit["scales"][index].tolist(), separators=(",", ":")),
        "D_local_maximum": "" if index in failed else solved[index]["D_local_maximum"],
        "first_exit_time": "" if index in failed else solved[index]["first_exit_time"],
        "exit_dimension": "" if index in failed else solved[index]["exit_dimension"],
    }
