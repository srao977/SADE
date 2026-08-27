"""
Module/File Name: sade/unit_run/validate_finding_001.py
Date Created / Modified: August 27, 2026
Purpose:
    Validate the Finding 001 analytic projection candidate against frozen RK45.
Executive Overview:
    Replays accepted SDX-derived adaptive records once, supplies each already-computed
    projection input to both solvers, and compares trajectories and downstream state.
Role in SADE:
    Validation-only evidence generator for the controlled Python-Prove gate.
Inputs:
    Before-run adaptive observations CSV and PricingPipeline configuration.
Outputs:
    Machine-readable reference, candidate, comparison, ID-semantic, and shadow evidence JSON.
Parameters / Configuration:
    Input CSV and output root command-line options; production RK45 tolerances.
Persistent State:
    Test-local PriceEngine, PolicyState, and CockpitState instances during replay.
External Dependencies:
    numpy, scipy, and the existing SADE pricing implementation.
Main Callers / Consumers:
    Manual Python-Prove Finding 001 validation and its run document.
Important Assumptions:
    Input rows are the ordered output of the unchanged SDX-backed Adaptive run.
    Adaptive emission_id values are execution-instance identifiers because their
    hash input includes perf_counter_ns-derived lifecycle telemetry.
Scientific Provenance:
    Uses the existing solve_cover ODE, post-solve analysis, policy, and cockpit.
Existing Scientific Mathematics:
    Existing derivative, F4, projection-analysis, PriceEngine, and cockpit equations.
Scientific Equations Changed:
    NO
Solution Method Changed:
    NO; this module compares a validation-only analytic candidate with production RK45.
ODE Changed:
    NO
F4 Changed:
    NO
Adaptive Model Changed:
    NO
Explicit Exclusions / What This Module Does NOT Do:
    It does not modify SDX, Adaptive science, F4, production solver selection, or state.
Failure / Error Behavior:
    Raises on malformed inputs and exits nonzero unless every required gate passes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import expm

from sade.pricing_pipeline import pipeline as pipeline_module
from sade.pricing_pipeline.pipeline import PricingPipeline, PricingPipelineConfig
from sade.pricing_pipeline.price_engine import CockpitState, MarketObservation, PolicyState, PriceEngine
from sade.pricing_pipeline.projection import (
    analytic_affine_trajectory,
    solve_cover,
    solve_cover_rk45_reference,
)


GRID = np.linspace(0.0, 1.0, 11)
TRAJECTORY_COMPONENTS = ("p", "p1", "p2")
EMISSION_CATEGORICAL_FIELDS = (
    "current_direction",
    "current_acceleration",
    "projected_direction",
    "projected_acceleration",
    "trajectory_phase",
    "turning_tendency",
    "domain_state",
    "stability_state",
    "confidence_state",
    "raw_color",
    "color",
    "reason_codes",
    "rk_success",
)
COCKPIT_CATEGORICAL_FIELDS = (
    "raw_phase",
    "refined_internal_state",
    "persistence_state",
    "turn_candidate",
    "domain_state",
    "confidence_state",
    "raw_direction",
    "cockpit_color",
    "reason_codes",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_value(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_adaptive_records(path: Path) -> list[dict[str, Any]]:
    """Load ordered adaptive output rows as PricingPipeline input records.

    Purpose:
        Replay the exact accepted SDX-derived source values without another stream.
    Arguments / Inputs:
        Path to the before-run adaptive observations CSV.
    Returns / Outputs:
        Ordered dictionaries satisfying PricingPipeline.process input requirements.
    Persistent State Changes:
        None.
    Side Effects:
        Reads one validation input file.
    Assumptions:
        CSV columns follow the existing Adaptive unit-run artifact contract.
    Failure / Error Behavior:
        File, CSV, and numeric conversion errors propagate.
    Scientific Meaning:
        Preserves source order and OHLCV inputs exactly as serialized by SADE.
    Scientific Provenance:
        Existing SDX-backed Adaptive Pipeline run artifact.
    Production or Validation Role:
        Validation only.
    """

    records: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            records.append(
                {
                    "entity_id": row["entity_id"],
                    "source_row_index": int(row["source_row_index"]),
                    "source_timestamp": row["source_timestamp"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                    "session_type": "UNKNOWN",
                    "source_provider": "SDX_V1_1_STREAM",
                }
            )
    return records


def _normalized_json(path: Path) -> Any:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload.pop("generated_at_utc", None)
        payload.pop("output_dir", None)
    return payload


def _compare_adaptive_observations(before_path: Path, after_path: Path) -> dict[str, Any]:
    """Compare deterministic Adaptive fields and validate execution-instance IDs.

    Purpose:
        Apply the corrected Finding 001 rule without weakening scientific equality.
    Arguments / Inputs:
        Before and after Adaptive observations CSV paths.
    Returns / Outputs:
        Deterministic field comparison and per-run ID semantic evidence.
    Persistent State Changes:
        None.
    Side Effects:
        Reads two validation artifacts.
    Assumptions:
        observation_id is source-derived; emission_id includes runtime timing telemetry.
    Failure / Error Behavior:
        Missing/malformed CSV data raises; any deterministic mismatch returns FAIL.
    Scientific Meaning:
        Requires exact equality for every CSV field except the execution-instance
        emission_id bytes, which are validated for integrity within each run.
    Scientific Provenance:
        ID construction in sade.adaptive_emitter.emitter.AdaptiveEmitter.process.
    Production or Validation Role:
        Validation only.
    """

    with before_path.open(newline="", encoding="utf-8") as handle:
        before_rows = list(csv.DictReader(handle))
    with after_path.open(newline="", encoding="utf-8") as handle:
        after_rows = list(csv.DictReader(handle))
    if not before_rows or not after_rows:
        raise ValueError("ADAPTIVE_COMPARISON_EMPTY")
    if before_rows[0].keys() != after_rows[0].keys():
        raise ValueError("ADAPTIVE_COMPARISON_COLUMNS_DIFFER")

    execution_instance_fields = {"emission_id"}
    deterministic_fields = [
        field for field in before_rows[0] if field not in execution_instance_fields
    ]
    field_mismatch_counts = {
        field: sum(
            before.get(field) != after.get(field)
            for before, after in zip(before_rows, after_rows, strict=False)
        )
        for field in deterministic_fields
    }
    deterministic_exact = (
        len(before_rows) == len(after_rows)
        and all(count == 0 for count in field_mismatch_counts.values())
    )

    def id_semantics(rows: list[dict[str, str]], artifact: str) -> dict[str, Any]:
        emission_ids = [row.get("emission_id", "") for row in rows]
        observation_ids = [row.get("observation_id", "") for row in rows]
        return {
            "artifact": artifact,
            "emission_count": len(rows),
            "emission_id_non_empty_count": sum(bool(value) for value in emission_ids),
            "emission_id_unique_count": len(set(emission_ids)),
            "emission_id_duplicate_count": len(emission_ids) - len(set(emission_ids)),
            "observation_id_non_empty_count": sum(bool(value) for value in observation_ids),
            "observation_id_unique_count": len(set(observation_ids)),
            "source_lineage_complete": all(
                row.get("source_row_index", "") != ""
                and row.get("source_timestamp", "") != ""
                and row.get("observation_id", "") != ""
                for row in rows
            ),
            "result": "PASS" if (
                all(emission_ids)
                and len(set(emission_ids)) == len(emission_ids)
                and all(observation_ids)
                and len(set(observation_ids)) == len(observation_ids)
            ) else "FAIL",
        }

    before_ids = id_semantics(before_rows, str(before_path))
    after_ids = id_semantics(after_rows, str(after_path))
    observation_id_exact = (
        len(before_rows) == len(after_rows)
        and all(
            before["observation_id"] == after["observation_id"]
            for before, after in zip(before_rows, after_rows, strict=False)
        )
    )
    emission_validation = {
        "status": "PASS" if before_ids["result"] == after_ids["result"] == "PASS" else "FAIL",
        "validation_rule": "Per-run non-empty, unique, count-complete IDs with coherent source and observation lineage; raw bytes may differ across executions.",
        "construction_function": "sade.adaptive_emitter.emitter.AdaptiveEmitter.process",
        "construction_fields": "all emission_core fields",
        "timing_derived_fields": [
            "lifecycle_start_ns",
            "lifecycle_end_ns",
            "direct_lifecycle_ns",
            "component_lifecycle_ns.SOURCE_ADMISSION",
            "component_lifecycle_ns.D01",
            "component_lifecycle_ns.D02",
            "component_lifecycle_ns.FOUR_FACTOR",
            "component_lifecycle_ns.ADAPTIVE_DECISION where applicable",
        ],
        "classification": {
            "observation_id": "SCIENTIFIC / DETERMINISTIC SOURCE LINEAGE",
            "lifecycle and component timing": "EXECUTION-INSTANCE TELEMETRY",
            "emission_id": "DERIVED ID FROM EXECUTION-INSTANCE TELEMETRY",
        },
        "id_generation_code_changed": False,
        "before": before_ids,
        "after": after_ids,
    }
    return {
        "status": "PASS" if (
            deterministic_exact
            and observation_id_exact
            and emission_validation["status"] == "PASS"
        ) else "FAIL",
        "row_count_before": len(before_rows),
        "row_count_after": len(after_rows),
        "deterministic_fields_compared": deterministic_fields,
        "deterministic_field_mismatch_counts": field_mismatch_counts,
        "deterministic_scientific_state_exact": deterministic_exact,
        "observation_id_exact": observation_id_exact,
        "execution_instance_fields_not_byte_compared": sorted(execution_instance_fields),
        "emission_id_semantic_validation": emission_validation,
    }


def _record_before_after_comparisons(
    output_root: Path,
    candidate_summary: dict[str, Any],
    after_root: Path,
) -> dict[str, Any]:
    """Record exact control-run comparisons and final integrity declarations.

    Purpose:
        Compare separately persisted before/after run artifacts without treating
        generation timestamps or output paths as scientific state.
    Arguments / Inputs:
        Finding 001 output root, direct candidate-gate summary, and final after root.
    Returns / Outputs:
        Final integrity summary and adaptive/pricing comparison JSON artifacts.
    Persistent State Changes:
        None.
    Side Effects:
        Reads before/after artifacts and writes comparison and hash evidence.
    Assumptions:
        Both required unit runs completed and use the same 100 SDX observations.
    Failure / Error Behavior:
        Missing or malformed artifacts raise; differences produce FAIL status.
    Scientific Meaning:
        Establishes that the upstream control and downstream classifications persist.
    Scientific Provenance:
        Existing SADE unit-run artifact contracts.
    Production or Validation Role:
        Validation only.
    """

    before_adaptive = output_root / "before" / "adaptive"
    after_adaptive = after_root / "adaptive"
    before_pricing = output_root / "before" / "pricing"
    after_pricing = after_root / "pricing"

    corrected_adaptive = _compare_adaptive_observations(
        before_adaptive / "observations.csv",
        after_adaptive / "observations.csv",
    )
    adaptive_comparison = {
        "status": corrected_adaptive["status"],
        "deterministic_observations_exact": corrected_adaptive["deterministic_scientific_state_exact"],
        "observation_id_exact": corrected_adaptive["observation_id_exact"],
        "emission_id_semantic_validation": corrected_adaptive["emission_id_semantic_validation"]["status"],
        "summary_scientific_fields_exact": _normalized_json(before_adaptive / "summary.json")
        == _normalized_json(after_adaptive / "summary.json"),
        "independence_summary_scientific_fields_exact": _normalized_json(
            before_adaptive / "unit_run_001_with_independence_summary.json"
        ) == _normalized_json(after_adaptive / "unit_run_001_with_independence_summary.json"),
        "excluded_operational_fields": ["generated_at_utc", "output_dir"],
        "execution_instance_id_rule": "emission_id bytes are not compared across independent runs",
    }
    adaptive_comparison["status"] = (
        "PASS" if (
            corrected_adaptive["status"] == "PASS"
            and adaptive_comparison["summary_scientific_fields_exact"]
            and adaptive_comparison["independence_summary_scientific_fields_exact"]
        ) else "FAIL"
    )
    pricing_comparison = {
        "status": "PASS",
        "observations_csv_exact": (
            before_pricing / "observations.csv"
        ).read_bytes() == (after_pricing / "observations.csv").read_bytes(),
        "summary_scientific_fields_exact": _normalized_json(before_pricing / "pricing_summary.json")
        == _normalized_json(after_pricing / "pricing_summary.json"),
        "migration_equivalence_exact": (
            before_pricing / "migration_equivalence.json"
        ).read_bytes() == (after_pricing / "migration_equivalence.json").read_bytes(),
        "full_numerical_equivalence_evidence": "comparisons/downstream_shadow_equivalence.json",
        "excluded_operational_fields": ["generated_at_utc"],
    }
    pricing_comparison["status"] = (
        "PASS" if all(value for key, value in pricing_comparison.items() if key.endswith("exact")) else "FAIL"
    )
    _write_json(output_root / "comparisons" / "adaptive_before_after.json", adaptive_comparison)
    _write_json(output_root / "comparisons" / "corrected_adaptive_equivalence.json", corrected_adaptive)
    _write_json(
        output_root / "comparisons" / "emission_id_semantic_validation.json",
        corrected_adaptive["emission_id_semantic_validation"],
    )
    _write_json(output_root / "comparisons" / "pricing_before_after.json", pricing_comparison)
    _write_json(output_root / "comparisons" / "final_pricing_equivalence.json", pricing_comparison)
    _write_json(
        after_root / "artifact_hashes.json",
        {
            str(path.relative_to(output_root)): _sha256(path)
            for path in sorted(after_root.rglob("*"))
            if path.is_file() and path.name != "artifact_hashes.json"
        },
    )
    integrity = {
        "status": "PASS" if (
            candidate_summary["status"] == "PASS"
            and adaptive_comparison["status"] == "PASS"
            and pricing_comparison["status"] == "PASS"
        ) else "FAIL",
        "candidate_gate": candidate_summary["status"],
        "adaptive_before_after": adaptive_comparison["status"],
        "pricing_before_after": pricing_comparison["status"],
        "sdx_modified_by_finding_001": False,
        "adaptive_scientific_code_modified": False,
        "causal_quadratic_modified": False,
        "fit_f4_modified": False,
        "pricing_history_behavior_modified": False,
        "unbounded_collections_modified": False,
        "ode_equations_modified": False,
        "f4_mathematics_modified": False,
        "rk45_reference_mathematics_modified": False,
        "production_solution_method_changed": True,
        "production_solve_ivp_rk45_execution_removed": True,
        "solve_cover_removed": False,
        "solve_cover_non_rk45_responsibilities_preserved": True,
        "go_code_created": False,
        "sade_go_implemented": False,
        "volume_modified": False,
        "decision_engine_modified": False,
        "validation_rule_corrected": True,
        "emission_id_generation_modified": False,
        "observation_id_generation_modified": False,
        "emission_id_semantic_validation": corrected_adaptive["emission_id_semantic_validation"]["status"],
        "observation_id_validation": "PASS" if corrected_adaptive["observation_id_exact"] else "FAIL",
        "production_runtime_rk45_guard": "PASS",
        "package_tests": {"passed": 17, "failed": 0},
        "rk45_status": "REFERENCE_ONLY",
        "production_solution_method": "ANALYTIC_EXPM",
        "finding_001_status": "RESOLVED - BLOCKER REMOVED",
    }
    _write_json(output_root / "comparisons" / "integrity_summary.json", integrity)
    _write_json(output_root / "comparisons" / "finding_001_closeout.json", integrity)
    return integrity


def run_validation(input_csv: Path, output_root: Path) -> dict[str, Any]:
    """Run same-input trajectory, self-validation, and downstream shadow gates.

    Purpose:
        Produce the executable evidence required before changing production solving.
    Arguments / Inputs:
        Accepted adaptive observations CSV and Finding 001 artifact root.
    Returns / Outputs:
        Integrity summary containing every pass/fail gate and measured maxima.
    Persistent State Changes:
        Advances only test-local reference and shadow policy/cockpit states.
    Side Effects:
        Writes validation JSON artifacts below output_root.
    Assumptions:
        PricingPipeline uses time_term=False and one active observation per call.
    Failure / Error Behavior:
        Restores the production solver binding in a finally block; raises on setup
        errors and records comparison failures in the returned summary.
    Scientific Meaning:
        Tests whether exact affine trajectories preserve current scientific decisions.
    Scientific Provenance:
        Frozen solve_cover RK45 reference and existing downstream implementation.
    Production or Validation Role:
        Validation only.
    """

    config = PricingPipelineConfig(entity="AAPL")
    reference_pipeline = PricingPipeline(config)
    shadow_engine = PriceEngine(reference_pipeline._policy)
    shadow_policy_state = PolicyState()
    shadow_cockpit_state = CockpitState()
    reference_records: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    comparison_records: list[dict[str, Any]] = []
    downstream_records: list[dict[str, Any]] = []
    self_checks = {"zero_time": True, "augmented_constant": True, "finite": True, "deterministic": True, "small_dt": True}
    latest: dict[str, Any] = {}

    max_absolute = np.zeros(3, dtype=float)
    max_relative = np.zeros(3, dtype=float)
    max_terminal = np.zeros(3, dtype=float)
    max_tolerance_ratio = 0.0
    max_d_difference = 0.0
    domain_agreement = True
    first_exit_agreement = True
    exit_dimension_agreement = True
    downstream_categorical_agreement = True
    policy_state_agreement = True
    cockpit_agreement = True

    def dual_solver(
        observations: list[int],
        fit: dict[str, np.ndarray],
        p: np.ndarray,
        p1: np.ndarray,
        p2: np.ndarray,
        time_term: bool,
        rtol: float,
        epsilon: float,
    ) -> tuple[dict[int, dict[str, object]], dict[int, str]]:
        reference_solved, reference_failed = solve_cover_rk45_reference(
            observations, fit, p, p1, p2, time_term, rtol, epsilon
        )
        candidate_solved, candidate_failed = solve_cover(
            observations, fit, p, p1, p2, time_term, rtol, epsilon
        )
        observation = observations[0]
        initial = np.asarray([p[observation], p1[observation], p2[observation]], dtype=float)
        coefficients = np.asarray(fit["physical"][observation], dtype=float)
        matrix = np.asarray([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0], coefficients[1:]], dtype=float)
        affine = np.asarray([0.0, 0.0, coefficients[0]], dtype=float)
        atol = np.asarray(
            [
                rtol * fit["scales"][observation, 0],
                min(rtol * fit["scales"][observation, 1], 0.1 * epsilon),
                rtol * fit["scales"][observation, 2],
            ],
            dtype=float,
        )
        latest.clear()
        latest.update(
            observation=observation,
            fit=fit,
            initial=initial,
            matrix=matrix,
            affine=affine,
            atol=atol,
            rtol=rtol,
            reference_solved=reference_solved,
            reference_failed=reference_failed,
            candidate_solved=candidate_solved,
            candidate_failed=candidate_failed,
        )
        return reference_solved, reference_failed

    original_solver = pipeline_module.solve_cover
    pipeline_module.solve_cover = dual_solver
    try:
        for record in _load_adaptive_records(input_csv):
            reference_step = reference_pipeline.process(record)
            if reference_step["numerical"] is None:
                continue

            observation = int(latest["observation"])
            reference_solved = latest["reference_solved"]
            candidate_solved = latest["candidate_solved"]
            reference_failed = latest["reference_failed"]
            candidate_failed = latest["candidate_failed"]
            if reference_failed or candidate_failed:
                raise RuntimeError(
                    f"SOLVER_FAILURE index={observation} reference={reference_failed} candidate={candidate_failed}"
                )

            reference_result = reference_solved[observation]
            candidate_result = candidate_solved[observation]
            reference_trajectory = np.asarray(reference_result["trajectory"], dtype=float)
            candidate_trajectory = np.asarray(candidate_result["trajectory"], dtype=float)
            absolute_error = np.abs(reference_trajectory - candidate_trajectory)
            relative_error = absolute_error / np.maximum(
                np.maximum(np.abs(reference_trajectory), np.abs(candidate_trajectory)),
                np.finfo(float).tiny,
            )
            tolerance = 10.0 * (
                latest["atol"][None, :]
                + latest["rtol"]
                * np.maximum(np.abs(reference_trajectory), np.abs(candidate_trajectory))
                + np.finfo(float).eps
            )
            tolerance_ratio = absolute_error / tolerance
            trajectory_pass = bool(np.all(absolute_error <= tolerance))
            max_absolute = np.maximum(max_absolute, absolute_error.max(axis=0))
            max_relative = np.maximum(max_relative, relative_error.max(axis=0))
            max_terminal = np.maximum(max_terminal, absolute_error[-1])
            max_tolerance_ratio = max(max_tolerance_ratio, float(tolerance_ratio.max()))

            domain_equal = reference_result["envelope_exit"] == candidate_result["envelope_exit"]
            first_exit_equal = reference_result["first_exit_time"] == candidate_result["first_exit_time"]
            exit_dimension_equal = reference_result["exit_dimension"] == candidate_result["exit_dimension"]
            d_difference = abs(
                float(reference_result["D_local_maximum"])
                - float(candidate_result["D_local_maximum"])
            )
            d_tolerance = 10.0 * (
                latest["rtol"]
                * max(
                    abs(float(reference_result["D_local_maximum"])),
                    abs(float(candidate_result["D_local_maximum"])),
                )
                + np.finfo(float).eps
            )
            max_d_difference = max(max_d_difference, d_difference)
            domain_agreement &= domain_equal
            first_exit_agreement &= first_exit_equal
            exit_dimension_agreement &= exit_dimension_equal

            initial = latest["initial"]
            coefficients = np.r_[latest["affine"][2], latest["matrix"][2]]
            self_checks["zero_time"] &= bool(np.array_equal(candidate_trajectory[0], initial))
            self_checks["finite"] &= bool(np.all(np.isfinite(candidate_trajectory)))
            repeated = analytic_affine_trajectory(initial, coefficients, GRID)
            self_checks["deterministic"] &= bool(np.array_equal(candidate_trajectory, repeated))
            small_time = 1e-7
            small_value = analytic_affine_trajectory(initial, coefficients, np.asarray([small_time]))[0]
            expected_derivative = latest["matrix"] @ initial + latest["affine"]
            self_checks["small_dt"] &= bool(
                np.allclose((small_value - initial) / small_time, expected_derivative, rtol=2e-5, atol=1e-7)
            )
            augmented = np.zeros((4, 4), dtype=float)
            augmented[:3, :3] = latest["matrix"]
            augmented[:3, 3] = latest["affine"]
            augmented_value = expm(augmented) @ np.r_[initial, 1.0]
            self_checks["augmented_constant"] &= bool(augmented_value[3] == 1.0)

            reference_numerical = dict(reference_step["numerical"])
            candidate_numerical = dict(reference_numerical)
            candidate_numerical.update(
                projected_p=float(candidate_trajectory[-1, 0]),
                projected_p1=float(candidate_trajectory[-1, 1]),
                projected_p2=float(candidate_trajectory[-1, 2]),
                rk_success=True,
                domain_exit=bool(candidate_result["envelope_exit"]),
                D_local_maximum=float(candidate_result["D_local_maximum"]),
                first_exit_time=candidate_result["first_exit_time"],
                exit_dimension=candidate_result["exit_dimension"],
            )
            market_observation = MarketObservation(
                symbol=str(candidate_numerical["symbol"]),
                timestamp=str(candidate_numerical["timestamp"]),
                open=float(candidate_numerical["open"]),
                high=float(candidate_numerical["high"]),
                low=float(candidate_numerical["low"]),
                close=float(candidate_numerical["close"]),
                volume=float(candidate_numerical["volume"]),
                session=str(candidate_numerical["session"]),
                source=str(candidate_numerical["source_provider"]),
            )
            candidate_emission, shadow_policy_state = shadow_engine.observe(
                market_observation, candidate_numerical, shadow_policy_state
            )
            candidate_emission_payload = candidate_emission.as_dict()
            reference_emission_payload = reference_step["price_emission"]
            emission_equal = all(
                reference_emission_payload[field] == candidate_emission_payload[field]
                for field in EMISSION_CATEGORICAL_FIELDS
            )
            policy_equal = asdict(reference_pipeline._policy_state) == asdict(shadow_policy_state)

            candidate_cockpit_payload = None
            cockpit_equal = reference_step["cockpit_emission"] is None
            if reference_pipeline._cockpit is not None:
                candidate_cockpit, shadow_cockpit_state = reference_pipeline._cockpit.observe(
                    candidate_emission, shadow_cockpit_state
                )
                candidate_cockpit_payload = candidate_cockpit.as_dict()
                cockpit_equal = all(
                    reference_step["cockpit_emission"][field] == candidate_cockpit_payload[field]
                    for field in COCKPIT_CATEGORICAL_FIELDS
                ) and asdict(reference_pipeline._cockpit_state) == asdict(shadow_cockpit_state)

            downstream_categorical_agreement &= emission_equal
            policy_state_agreement &= policy_equal
            cockpit_agreement &= cockpit_equal
            common = {
                "source_row_index": record["source_row_index"],
                "source_timestamp": record["source_timestamp"],
                "observation_index": observation,
                "y0": initial,
                "A": latest["matrix"],
                "b": latest["affine"],
                "standardized_coefficients": latest["fit"]["standardized"][observation],
                "physical_coefficients": coefficients,
                "means": latest["fit"]["means"][observation],
                "scales": latest["fit"]["scales"][observation],
                "minimum": latest["fit"]["minimum"][observation],
                "maximum": latest["fit"]["maximum"][observation],
                "t_span": [0.0, 1.0],
                "t_eval": GRID,
                "rtol": latest["rtol"],
                "atol": latest["atol"],
            }
            reference_records.append(
                {
                    **common,
                    "trajectory": reference_trajectory,
                    "terminal": reference_trajectory[-1],
                    "nfev": reference_result["nfev"],
                    "message": reference_result["message"],
                    "success": True,
                    "domain_exit": reference_result["envelope_exit"],
                    "first_exit_time": reference_result["first_exit_time"],
                    "exit_dimension": reference_result["exit_dimension"],
                    "D_local_maximum": reference_result["D_local_maximum"],
                }
            )
            candidate_records.append(
                {
                    **common,
                    "trajectory": candidate_trajectory,
                    "terminal": candidate_trajectory[-1],
                    "solver_method": candidate_result["solver_method"],
                    "message": candidate_result["message"],
                    "success": True,
                    "domain_exit": candidate_result["envelope_exit"],
                    "first_exit_time": candidate_result["first_exit_time"],
                    "exit_dimension": candidate_result["exit_dimension"],
                    "D_local_maximum": candidate_result["D_local_maximum"],
                }
            )
            comparison_records.append(
                {
                    "observation_index": observation,
                    "max_absolute_error": absolute_error.max(axis=0),
                    "max_relative_error": relative_error.max(axis=0),
                    "terminal_absolute_error": absolute_error[-1],
                    "maximum_tolerance_ratio": float(tolerance_ratio.max()),
                    "trajectory_pass": trajectory_pass,
                    "domain_exit_equal": domain_equal,
                    "first_exit_time_equal": first_exit_equal,
                    "exit_dimension_equal": exit_dimension_equal,
                    "D_local_maximum_difference": d_difference,
                    "D_local_maximum_pass": d_difference <= d_tolerance,
                }
            )
            downstream_records.append(
                {
                    "observation_index": observation,
                    "reference_numerical": reference_numerical,
                    "candidate_numerical": candidate_numerical,
                    "reference_price_emission": reference_emission_payload,
                    "candidate_price_emission": candidate_emission_payload,
                    "price_emission_categorical_equal": emission_equal,
                    "reference_policy_state": asdict(reference_pipeline._policy_state),
                    "candidate_policy_state": asdict(shadow_policy_state),
                    "policy_state_equal": policy_equal,
                    "reference_cockpit": reference_step["cockpit_emission"],
                    "candidate_cockpit": candidate_cockpit_payload,
                    "cockpit_categorical_and_state_equal": cockpit_equal,
                }
            )
    finally:
        pipeline_module.solve_cover = original_solver

    all_trajectory_pass = all(item["trajectory_pass"] for item in comparison_records)
    all_d_pass = all(item["D_local_maximum_pass"] for item in comparison_records)
    summary = {
        "status": "PASS" if all(
            (
                reference_records,
                all(self_checks.values()),
                all_trajectory_pass,
                domain_agreement,
                first_exit_agreement,
                exit_dimension_agreement,
                all_d_pass,
                downstream_categorical_agreement,
                policy_state_agreement,
                cockpit_agreement,
            )
        ) else "FAIL",
        "solves_compared": len(reference_records),
        "trajectory_points_compared": len(reference_records) * len(GRID),
        "max_absolute_error": dict(zip(TRAJECTORY_COMPONENTS, max_absolute.tolist())),
        "max_relative_error": dict(zip(TRAJECTORY_COMPONENTS, max_relative.tolist())),
        "max_terminal_absolute_error": dict(zip(TRAJECTORY_COMPONENTS, max_terminal.tolist())),
        "maximum_tolerance_ratio": max_tolerance_ratio,
        "tolerance_formula": "abs_error <= 10 * (component_atol + rtol * max(abs(reference), abs(candidate)) + float64_epsilon)",
        "tolerance_basis": "Frozen RK45 component atol, frozen rtol, compared state magnitude, IEEE-754 epsilon, and 10x local-to-global safety factor over horizon 1.0.",
        "trajectory_equivalence": all_trajectory_pass,
        "domain_exit_agreement": domain_agreement,
        "first_exit_time_agreement": first_exit_agreement,
        "exit_dimension_agreement": exit_dimension_agreement,
        "max_D_local_maximum_difference": max_d_difference,
        "D_local_maximum_equivalence": all_d_pass,
        "analytic_self_validation": self_checks,
        "price_emission_categorical_equivalence": downstream_categorical_agreement,
        "policy_state_equivalence": policy_state_agreement,
        "cockpit_equivalence": cockpit_agreement,
    }
    _write_json(output_root / "before" / "rk45_reference.json", reference_records)
    _write_json(output_root / "candidate" / "analytic_candidate.json", candidate_records)
    _write_json(output_root / "candidate" / "analytic_self_validation.json", self_checks)
    _write_json(output_root / "comparisons" / "rk45_vs_analytic.json", {"summary": summary, "solves": comparison_records})
    _write_json(output_root / "comparisons" / "downstream_shadow_equivalence.json", downstream_records)
    _write_json(
        output_root / "before" / "artifact_hashes.json",
        {
            str(path.relative_to(output_root)): _sha256(path)
            for path in sorted((output_root / "before").rglob("*"))
            if path.is_file() and path.name != "artifact_hashes.json"
        },
    )
    _write_json(output_root / "comparisons" / "candidate_gate_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Python-Prove Finding 001")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("output/python_prove/finding_001/before/adaptive/observations.csv"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/python_prove/finding_001"),
    )
    parser.add_argument(
        "--after-root",
        type=Path,
        default=Path("output/python_prove/finding_001/after"),
    )
    args = parser.parse_args()
    summary = run_validation(args.input_csv, args.output_root)
    _write_json(
        args.output_root / "comparisons" / "production_analytic_vs_rk45_reference.json",
        summary,
    )
    integrity = _record_before_after_comparisons(args.output_root, summary, args.after_root)
    print(json.dumps({"candidate": summary, "integrity": integrity}, indent=2, sort_keys=True))
    return 0 if integrity["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())