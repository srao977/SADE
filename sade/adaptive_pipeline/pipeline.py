"""
Module/File Name: sade/adaptive_pipeline/pipeline.py
Date Created / Migrated: August 25, 2026
Purpose:
    Implement SADE Adaptive Pipeline orchestration with zero runtime dependency
    on APTF repository paths.
Executive Overview:
    The pipeline requests SDX MarketVectors, validates causal order and entity,
    maps vectors into the frozen adaptive emitter seam, and writes SADE-owned
    unit-run outputs.
Role in SADE:
    V0.1 primary product capability runtime.
Inputs:
    SDX stream vectors, pipeline configuration, SADE-owned baseline metadata.
Outputs:
    observations.csv, summary.json, and in-memory summary dictionary.
Parameters / Configuration:
    AdaptivePipelineConfig.
Persistent State:
    expected_next_index, vectors_received, collected observation rows.
External Dependencies:
    sade.input.sdx_client.SadeSdxClient
    sade.adaptive_emitter.AdaptiveEmitter
    sade.configuration.scientific_baseline
Main Callers / Consumers:
    sade CLI, sade.unit_run.run_001, tests.
Important Assumptions:
    data_valid=true and session_type=UNKNOWN are SADE assumptions/placeholders.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No D03 execution
    - No Price/Volume path execution
    - No timestamp normalization/cadence logic
Failure / Error Behavior:
    Raises explicit failures for malformed vectors, stream shortfall, entity
    mismatch, row-order regression, RPC failures, and emitter failures.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sade.adaptive_emitter import AdaptiveEmitter
from sade.configuration.scientific_baseline import get_baseline_fingerprints
from sade.input.sdx_client import DEFAULT_ENDPOINT, SadeSdxClient

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNIT_RUN_OUTPUT_DIR = ROOT / "output" / "unit_runs" / "001"


def physical_row_from_source_index(source_row_index: int) -> int:
    """Apply the validated compatibility rule for frozen emitter seam.

    Args:
        source_row_index: SDX source order index.

    Returns:
        physical_row identity expected by AdaptiveEmitter.process.
    """
    return int(source_row_index) + 2


def build_source_row(vector: Any) -> dict[str, str]:
    """Map an SDX MarketVector into adaptive emitter source row shape.

    Args:
        vector: MarketVector-like object.

    Returns:
        source_row dictionary.

    Raises:
        AttributeError: on missing required fields.
    """
    required = (
        "entity_id",
        "source_row_index",
        "source_timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    for name in required:
        if not hasattr(vector, name):
            raise AttributeError(f"MALFORMED_MARKETVECTOR missing field: {name}")

    return {
        "entity_id": str(vector.entity_id),
        "event_timestamp_utc": str(vector.source_timestamp),
        "open": str(vector.open),
        "high": str(vector.high),
        "low": str(vector.low),
        "close": str(vector.close),
        "volume": str(vector.volume),
        "source_row_number": str(int(vector.source_row_index)),
        "data_valid": "true",
        "session_type": "UNKNOWN",
    }


def _validate_vector(vector: Any, expected_entity: str, expected_index: int) -> None:
    """Validate entity and strict causal row progression."""
    required = (
        "entity_id",
        "source_row_index",
        "source_timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    for name in required:
        if not hasattr(vector, name):
            raise AttributeError(f"MALFORMED_MARKETVECTOR missing field: {name}")

    if str(vector.entity_id) != expected_entity:
        raise ValueError(f"ENTITY_MISMATCH expected={expected_entity} got={vector.entity_id}")
    if int(vector.source_row_index) != expected_index:
        raise ValueError(
            "ROW_ORDER_REGRESSION "
            f"expected_source_row_index={expected_index} got={vector.source_row_index}"
        )


def _build_record(
    observation_number: int,
    vector: Any,
    physical_row: int,
    emission: dict[str, Any],
    adaptation_event_delta: int,
    feedback_event_delta: int,
) -> dict[str, Any]:
    """Flatten source and emission fields for CSV persistence."""
    state_after = emission.get("state_after", {})
    mathematics = emission.get("mathematics", {})
    return_shape = mathematics.get("return_shape", {})
    prior_context_count = len(emission.get("prior_context_ids") or [])

    return {
        "pipeline_observation_number": observation_number,
        "source_row_index": int(vector.source_row_index),
        "source_timestamp": str(vector.source_timestamp),
        "entity_id": str(vector.entity_id),
        "open": float(vector.open),
        "high": float(vector.high),
        "low": float(vector.low),
        "close": float(vector.close),
        "volume": int(vector.volume),
        "physical_row": int(physical_row),
        "status": emission.get("status"),
        "observation_id": emission.get("observation_id"),
        "emission_id": emission.get("emission_id"),
        "source_delta_t_seconds": emission.get("source_delta_t_seconds"),
        "decision_rule_path": emission.get("decision_rule_path"),
        "H": mathematics.get("H"),
        "Q_G": mathematics.get("Q_G"),
        "Q_S": mathematics.get("Q_S"),
        "Q_R": mathematics.get("Q_R"),
        "C": mathematics.get("C"),
        "path_direction": return_shape.get("path_direction"),
        "terminal_displacement": return_shape.get("terminal_displacement"),
        "strength": return_shape.get("strength"),
        "coherence": return_shape.get("coherence"),
        "persistence": return_shape.get("persistence"),
        "uncertainty": return_shape.get("uncertainty"),
        "reversal_propensity": return_shape.get("reversal_propensity"),
        "position_decision": emission.get("position_decision"),
        "position_state_before": emission.get("position_state_before"),
        "position_state_after": state_after.get("position_state"),
        "prior_context_count": prior_context_count,
        "adaptation_event_delta": adaptation_event_delta,
        "feedback_event_delta": feedback_event_delta,
    }


@dataclass(frozen=True)
class AdaptivePipelineConfig:
    """Configuration for a bounded SADE adaptive pipeline run."""

    sdx_endpoint: str = DEFAULT_ENDPOINT
    entity: str = "AAPL"
    max_vectors: int = 100
    timeout_seconds: float = 60.0
    require_strict_row_increment: bool = True
    output_dir: Path = DEFAULT_UNIT_RUN_OUTPUT_DIR
    observations_csv_name: str = "observations.csv"
    summary_json_name: str = "summary.json"
    rule_fingerprint: str = ""
    code_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.entity.strip():
            raise ValueError("CONFIG_INVALID entity must be non-empty")
        if self.max_vectors <= 0:
            raise ValueError("CONFIG_INVALID max_vectors must be > 0")
        if self.timeout_seconds <= 0:
            raise ValueError("CONFIG_INVALID timeout_seconds must be > 0")


class AdaptivePipeline:
    """Run one entity stream through SADE adaptive scientific modules."""

    def __init__(self, config: AdaptivePipelineConfig, client: SadeSdxClient | None = None, emitter: Any | None = None) -> None:
        self.config = config
        self._client = client if client is not None else SadeSdxClient(endpoint=config.sdx_endpoint)

        if emitter is None:
            rule, code = (
                (config.rule_fingerprint, config.code_fingerprint)
                if config.rule_fingerprint and config.code_fingerprint
                else get_baseline_fingerprints()
            )
            self._emitter = AdaptiveEmitter(config.entity, rule, code)
        else:
            self._emitter = emitter

        self._rows: list[dict[str, Any]] = []
        self._expected_index = 0
        self._vectors_received = 0
        self._closed = False

    @property
    def observations_csv_path(self) -> Path:
        return self.config.output_dir / self.config.observations_csv_name

    @property
    def summary_json_path(self) -> Path:
        return self.config.output_dir / self.config.summary_json_name

    def process_vector(self, vector: Any) -> dict[str, Any]:
        """Process one MarketVector causally and return flattened record."""
        if self.config.require_strict_row_increment:
            _validate_vector(vector, self.config.entity, self._expected_index)

        before_adaptation = len(self._emitter.adaptation_audit)
        before_feedback = len(self._emitter.feedback_audit)

        source_row = build_source_row(vector)
        physical_row = physical_row_from_source_index(int(vector.source_row_index))
        observation_number = self._expected_index + 1

        try:
            emission = self._emitter.process(physical_row=physical_row, source_row=source_row)
        except Exception as error:
            raise RuntimeError(
                "ADAPTIVE_PROCESSING_FAILURE "
                f"observation={observation_number} source_row_index={vector.source_row_index}: {error}"
            ) from error

        adaptation_delta = len(self._emitter.adaptation_audit) - before_adaptation
        feedback_delta = len(self._emitter.feedback_audit) - before_feedback

        record = _build_record(
            observation_number=observation_number,
            vector=vector,
            physical_row=physical_row,
            emission=emission,
            adaptation_event_delta=adaptation_delta,
            feedback_event_delta=feedback_delta,
        )

        self._rows.append(record)
        self._expected_index += 1
        self._vectors_received += 1
        return record

    def run(self) -> dict[str, Any]:
        """Execute bounded stream run and serialize SADE-owned output files."""
        failures: list[str] = []
        status_counts: Counter[str] = Counter()
        decision_counts: Counter[str] = Counter()
        path_counts: Counter[str] = Counter()
        position_after_counts: Counter[str] = Counter()

        h_values: list[float] = []
        qg_values: list[float] = []
        qs_values: list[float] = []
        qr_values: list[float] = []
        c_values: list[float] = []
        delta_seconds: list[float] = []

        first_actionable: int | None = None

        try:
            stream = self._client.stream_vectors(
                entities=[self.config.entity],
                max_vectors_per_entity=self.config.max_vectors,
                timeout_seconds=self.config.timeout_seconds,
            )
            for vector in stream:
                row = self.process_vector(vector)
                status = str(row["status"])
                status_counts[status] += 1
                path_counts[str(row["path_direction"])] += 1
                position_after_counts[str(row["position_state_after"])] += 1

                if row["H"] is not None:
                    h_values.append(float(row["H"]))
                if row["Q_G"] is not None:
                    qg_values.append(float(row["Q_G"]))
                if row["Q_S"] is not None:
                    qs_values.append(float(row["Q_S"]))
                if row["Q_R"] is not None:
                    qr_values.append(float(row["Q_R"]))
                if row["C"] is not None:
                    c_values.append(float(row["C"]))
                if row["source_delta_t_seconds"] is not None:
                    delta_seconds.append(float(row["source_delta_t_seconds"]))

                if status == "ACTIONABLE" and first_actionable is None:
                    first_actionable = int(row["pipeline_observation_number"])

                decision = row["position_decision"]
                if decision in {"BUY", "SELL", "HOLD"}:
                    decision_counts[str(decision)] += 1

                if self._vectors_received >= self.config.max_vectors:
                    break

            if self._vectors_received != self.config.max_vectors:
                raise RuntimeError(
                    f"SHORT_STREAM expected={self.config.max_vectors} got={self._vectors_received}"
                )
        except Exception as error:
            failures.append(f"PIPELINE_FAILURE {type(error).__name__}: {error}")

        self._write_csv()
        summary = {
            "status": "FAILED" if failures else "COMPLETE",
            "entity": self.config.entity,
            "vectors_requested": self.config.max_vectors,
            "vectors_received": self._vectors_received,
            "initializing": int(status_counts.get("INITIALIZING", 0)),
            "actionable": int(status_counts.get("ACTIONABLE", 0)),
            "BUY": int(decision_counts.get("BUY", 0)),
            "SELL": int(decision_counts.get("SELL", 0)),
            "HOLD": int(decision_counts.get("HOLD", 0)),
            "first_actionable": first_actionable,
            "H_min": min(h_values) if h_values else None,
            "H_max": max(h_values) if h_values else None,
            "Q_G_min": min(qg_values) if qg_values else None,
            "Q_G_max": max(qg_values) if qg_values else None,
            "Q_S_min": min(qs_values) if qs_values else None,
            "Q_S_max": max(qs_values) if qs_values else None,
            "Q_R_min": min(qr_values) if qr_values else None,
            "Q_R_max": max(qr_values) if qr_values else None,
            "C_min": min(c_values) if c_values else None,
            "C_max": max(c_values) if c_values else None,
            "path_direction_counts": dict(path_counts),
            "position_state_after_counts": dict(position_after_counts),
            "source_timestamp_first": self._rows[0]["source_timestamp"] if self._rows else None,
            "source_timestamp_last": self._rows[-1]["source_timestamp"] if self._rows else None,
            "source_delta_t_seconds_min": min(delta_seconds) if delta_seconds else None,
            "source_delta_t_seconds_max": max(delta_seconds) if delta_seconds else None,
            "irregular_source_time_gap_count": sum(1 for x in delta_seconds if abs(x - 60.0) > 1e-9),
            "adaptation_event_count": len(self._emitter.adaptation_audit),
            "feedback_event_count": len(self._emitter.feedback_audit),
            "source_timestamp_preserved": True,
            "timestamp_normalization": False,
            "cadence_logic": "NONE",
            "assumptions": {
                "data_valid": "true (SADE INPUT ASSUMPTION - NOT SDX SOURCE DATA)",
                "session_type": "UNKNOWN (SADE PLACEHOLDER - NOT SDX SOURCE DATA)",
            },
            "failures": failures,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self.config.output_dir),
        }
        self.summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def _write_csv(self) -> None:
        """Write observations CSV in SADE-owned output directory."""
        fieldnames = list(self._rows[0].keys()) if self._rows else [
            "pipeline_observation_number",
            "source_row_index",
            "source_timestamp",
            "entity_id",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "physical_row",
            "status",
            "observation_id",
            "emission_id",
            "source_delta_t_seconds",
            "decision_rule_path",
            "H",
            "Q_G",
            "Q_S",
            "Q_R",
            "C",
            "path_direction",
            "terminal_displacement",
            "strength",
            "coherence",
            "persistence",
            "uncertainty",
            "reversal_propensity",
            "position_decision",
            "position_state_before",
            "position_state_after",
            "prior_context_count",
            "adaptation_event_delta",
            "feedback_event_delta",
        ]
        self.observations_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with self.observations_csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in self._rows:
                writer.writerow(row)

    def close(self) -> None:
        """Close pipeline resources."""
        if self._closed:
            return
        self._client.close()
        self._closed = True

    def __enter__(self) -> "AdaptivePipeline":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
