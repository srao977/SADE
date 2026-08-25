"""
Module/File Name: sade/pricing_pipeline/projection.py
Date Created / Migrated: August 25, 2026
Purpose:
    Provide RK45 one-step projection mathematics for SADE pricing pipeline.
Executive Overview:
    Integrates local dynamics over a fixed one-minute horizon and reports
    trajectory, domain-exit, and diagnostics.
Role in SADE:
    Projection stage between F4 local model and PriceEngine numerical assembly.
Inputs:
    Observation indices, fit dictionary, and p/p1/p2 arrays.
Outputs:
    Solved trajectories and explicit failure map.
Parameters / Configuration:
    RTOL, EPSILON and optional time-term toggle.
Persistent State:
    None.
External Dependencies:
    numpy and scipy.integrate.solve_ivp.
Main Callers / Consumers:
    sade.pricing_pipeline.pipeline and equivalence tests.
Important Assumptions:
    Projection horizon is fixed [0,1] minute and distinct from source timestamp gaps.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF diagnostics/run_test_013b_qqq_validation.py::solve_cover
Explicit Exclusions / What This Module Does NOT Do:
    - No cadence enforcement
    - No timestamp normalization
    - No policy classification
Failure / Error Behavior:
    Per-observation failures are captured in failed mapping with explicit error text.
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp


def solve_cover(
    observations: list[int],
    fit: dict[str, np.ndarray],
    p: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
    time_term: bool,
    rtol: float,
    epsilon: float,
) -> tuple[dict[int, dict[str, object]], dict[int, str]]:
    """Solve one-minute RK45 projection for selected observation indices.

    Purpose:
        Integrate local state dynamics from current [p,p1,p2] endpoint to horizon 1.0.
    Arguments / Inputs:
        observations, fit, p, p1, p2, time_term, rtol, epsilon.
    Returns / Outputs:
        (solved, failed) dictionaries keyed by observation index.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        fit arrays align to p/p1/p2 arrays and required indices are valid.
    Failure / Error Behavior:
        Integration and stability failures are stored in failed map.
    Scientific Meaning:
        One-step RK45 evolution under local affine dynamics.
    Original APTF Source:
        diagnostics/run_test_013b_qqq_validation.py::solve_cover
    Scientific Mathematics Changed:
        NO
    """

    solved: dict[int, dict[str, object]] = {}
    failed: dict[int, str] = {}
    grid = np.linspace(0.0, 1.0, 11)

    def run(group: list[int]) -> None:
        if not group:
            return
        indices = np.asarray(group, dtype=int)
        initial = np.column_stack((p[indices], p1[indices], p2[indices]))
        beta = fit["standardized"][indices]
        means = fit["means"][indices]
        scales = fit["scales"][indices]

        def function(time: float, flattened: np.ndarray) -> np.ndarray:
            state_values = flattened.reshape(-1, 3)
            standardized = (state_values - means) / scales
            jerk = beta[:, 0] + np.sum(beta[:, 1:4] * standardized, axis=1)
            if time_term:
                jerk += beta[:, 4] * ((time - fit["time_mean"][indices]) / fit["time_scale"][indices])
            return np.column_stack((state_values[:, 1], state_values[:, 2], jerk)).ravel()

        atol = np.column_stack(
            (
                rtol * scales[:, 0],
                np.minimum(rtol * scales[:, 1], 0.1 * epsilon),
                rtol * scales[:, 2],
            )
        ).ravel()

        try:
            solution = solve_ivp(
                function,
                (0.0, 1.0),
                initial.ravel(),
                method="RK45",
                rtol=rtol,
                atol=atol,
                t_eval=grid,
            )
            if not solution.success or not np.all(np.isfinite(solution.y)):
                raise RuntimeError(solution.message)
            trajectories = solution.y.reshape(len(group), 3, -1).transpose(0, 2, 1)
            for position, observation in enumerate(group):
                trajectory = trajectories[position]
                if np.any(np.abs(trajectory[-1] - initial[position]) > 1e6 * scales[position]):
                    failed[observation] = "NUMERICALLY_UNSTABLE"
                    continue
                local_distance = np.linalg.norm((trajectory - means[position]) / scales[position], axis=1)
                inside_components = (
                    (trajectory >= fit["minimum"][indices[position]])
                    & (trajectory <= fit["maximum"][indices[position]])
                )
                inside = np.all(inside_components, axis=1)
                exit_positions = np.flatnonzero(~inside)
                first_exit: float | str = ""
                exit_dimension = ""
                if len(exit_positions):
                    exit_position = int(exit_positions[0])
                    first_exit = float(grid[exit_position])
                    exit_dimension = "|".join(
                        np.asarray(["P", "P1", "P2"])[~inside_components[exit_position]].tolist()
                    )
                solved[observation] = {
                    "trajectory": trajectory,
                    "nfev": int(solution.nfev),
                    "message": solution.message,
                    "D_local_maximum": float(local_distance.max()),
                    "envelope_exit": bool(len(exit_positions)),
                    "first_exit_time": first_exit,
                    "exit_dimension": exit_dimension,
                }
        except Exception as error:
            if len(group) == 1:
                failed[group[0]] = str(error)
            else:
                midpoint = len(group) // 2
                run(group[:midpoint])
                run(group[midpoint:])

    for start in range(0, len(observations), 1024):
        run(observations[start : start + 1024])
    return solved, failed
