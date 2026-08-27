"""
Module/File Name: sade/pricing_pipeline/projection.py
Date Created / Modified: August 27, 2026
Purpose:
    Provide analytic projection mathematics and a frozen RK45 validation reference.
Executive Overview:
    Solves local affine dynamics over a fixed one-minute horizon with an augmented
    matrix exponential, then preserves the established trajectory analysis and result
    contract. Historical RK45 remains reference/validation only.
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
    numpy, scipy.integrate.solve_ivp, and scipy.linalg.expm.
Main Callers / Consumers:
    PricingPipeline calls analytic solve_cover; validation calls the RK45 reference.
Important Assumptions:
    Projection horizon is fixed [0,1] minute and distinct from source timestamp gaps.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF diagnostics/run_test_013b_qqq_validation.py::solve_cover
Existing Scientific Mathematics:
    The state derivative is [p1, p2, b + a_p*p + a_p1*p1 + a_p2*p2].
Scientific Equations Changed:
    NO
Projection Solution Method:
    ANALYTIC MATRIX EXPONENTIAL
Historical RK45:
    REFERENCE / VALIDATION ONLY
ODE Equations Changed:
    NO
F4 Changed:
    NO
Adaptive Model Changed:
    NO
Finding 002:
    NOT INCLUDED
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
from scipy.linalg import expm


def analytic_affine_trajectory(
    initial: np.ndarray,
    physical_coefficients: np.ndarray,
    evaluation_times: np.ndarray,
) -> np.ndarray:
    """Evaluate the exact affine projection trajectory on a requested grid.

    Purpose:
        Provide the shadow candidate for replacing RK45 trajectory generation.
    Arguments / Inputs:
        Three-component initial state, physical coefficients [b,a_p,a_p1,a_p2],
        and evaluation times measured from the initial state time.
    Returns / Outputs:
        Array shaped (number of times, 3) containing [p,p1,p2].
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Coefficients are finite and constant over the solve interval.
    Failure / Error Behavior:
        Raises ValueError for invalid shapes/non-finite inputs; scipy.linalg.expm
        errors propagate to the validation caller.
    Scientific Meaning:
        Solves dy/dt=A*y+b exactly by exponentiating the augmented affine system.
    Scientific Provenance:
        ODE source is the existing solve_cover vector field.
    Production or Validation Role:
        Validation only until the Finding 001 equivalence gate passes.
    ODE Changed:
        NO
    Solver:
        Exact affine matrix-exponential solution using scipy.linalg.expm.
    """

    initial_array = np.asarray(initial, dtype=float)
    coefficients = np.asarray(physical_coefficients, dtype=float)
    times = np.asarray(evaluation_times, dtype=float)
    if initial_array.shape != (3,):
        raise ValueError("ANALYTIC_INITIAL_SHAPE expected=(3,)")
    if coefficients.shape != (4,):
        raise ValueError("ANALYTIC_COEFFICIENT_SHAPE expected=(4,)")
    if times.ndim != 1:
        raise ValueError("ANALYTIC_TIME_GRID must be one-dimensional")
    if not np.all(np.isfinite(initial_array)) or not np.all(np.isfinite(coefficients)):
        raise ValueError("ANALYTIC_INPUT_NONFINITE")
    if not np.all(np.isfinite(times)):
        raise ValueError("ANALYTIC_TIME_GRID_NONFINITE")

    augmented_matrix = np.zeros((4, 4), dtype=float)
    augmented_matrix[:3, :3] = np.asarray(
        [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], coefficients[1:]],
        dtype=float,
    )
    augmented_matrix[:3, 3] = np.asarray([0.0, 0.0, coefficients[0]], dtype=float)
    augmented_initial = np.r_[initial_array, 1.0]
    return np.asarray(
        [(expm(augmented_matrix * float(time)) @ augmented_initial)[:3] for time in times],
        dtype=float,
    )


def solve_cover_rk45_reference(
    observations: list[int],
    fit: dict[str, np.ndarray],
    p: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
    time_term: bool,
    rtol: float,
    epsilon: float,
) -> tuple[dict[int, dict[str, object]], dict[int, str]]:
    """Run the frozen one-minute RK45 validation reference.

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
    Production Role:
        NO
    Validation Role:
        YES
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
    """Solve cover with exact affine matrix-exponential trajectories.

    Purpose:
        Generate production trajectories while preserving established cover analysis.
    Arguments / Inputs:
        The exact solve_cover observations, fit, state arrays, time-term flag,
        tolerance, and epsilon inputs. The tolerances are accepted to preserve the
        comparison signature but do not control exact matrix exponentiation.
    Returns / Outputs:
        Candidate (solved, failed) dictionaries keyed by observation index.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        time_term is false, making each three-state ODE affine and constant over
        the fixed [0,1] interval; fit physical coefficients match standardized fit.
    Failure / Error Behavior:
        Rejects time_term because that existing branch is explicitly time-varying;
        per-observation analytic or stability failures enter the failed mapping.
    Scientific Meaning:
        Preserves solve_cover setup, stability screening, sampled domain exit,
        D_local_maximum, and output packaging while replacing only trajectory solving.
    Scientific Provenance:
        ODE source and post-solve analysis are the existing solve_cover implementation.
    Production or Validation Role:
        Production; PricingPipeline calls this function directly.
    ODE Changed:
        NO
    Solver:
        Exact affine matrix-exponential solution using scipy.linalg.expm.
    """

    del rtol, epsilon
    if time_term:
        raise ValueError("ANALYTIC_TIME_TERM_UNSUPPORTED")

    solved: dict[int, dict[str, object]] = {}
    failed: dict[int, str] = {}
    grid = np.linspace(0.0, 1.0, 11)
    for observation in observations:
        initial = np.asarray([p[observation], p1[observation], p2[observation]], dtype=float)
        scales = fit["scales"][observation]
        try:
            trajectory = analytic_affine_trajectory(initial, fit["physical"][observation], grid)
            if not np.all(np.isfinite(trajectory)):
                raise RuntimeError("ANALYTIC_NONFINITE_TRAJECTORY")
            if np.any(np.abs(trajectory[-1] - initial) > 1e6 * scales):
                failed[observation] = "NUMERICALLY_UNSTABLE"
                continue
            local_distance = np.linalg.norm(
                (trajectory - fit["means"][observation]) / scales,
                axis=1,
            )
            inside_components = (
                (trajectory >= fit["minimum"][observation])
                & (trajectory <= fit["maximum"][observation])
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
                "solver_method": "ANALYTIC_EXPM",
                "message": "ANALYTIC_EXPM_SUCCESS",
                "D_local_maximum": float(local_distance.max()),
                "envelope_exit": bool(len(exit_positions)),
                "first_exit_time": first_exit,
                "exit_dimension": exit_dimension,
            }
        except Exception as error:
            failed[observation] = str(error)
    return solved, failed
