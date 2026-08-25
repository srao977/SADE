"""
Module/File Name: sade/adaptive_emitter/emitter.py
Date Created / Migrated: August 25, 2026
Purpose:
    Execute the SADE V0.1 adaptive scientific path for one causal observation
    at a time.
Executive Overview:
    This module is the migrated adaptive emitter implementation used by SADE
    Adaptive Pipeline. It preserves validated decision/state behavior from the
    frozen adaptive lineage while using SADE-owned imports.
Role in SADE:
    Core adaptive scientific executor for V0.1.
Inputs:
    physical_row and source_row records passed by the adaptive pipeline.
Outputs:
    immutable emission dictionaries, initialization records, adaptation audit,
    and feedback audit entries.
Parameters / Configuration:
    entity_id, rule_fingerprint, code_fingerprint.
Persistent State:
    rolling context, position state, previous decision, completed_count,
    adaptation and feedback audit collections.
External Dependencies:
    sade.d01.v02.model.D01V02Model
    sade.d02.v02.builder.build_return_shape
    sade.d04.envelope.capturability_model.CapturabilityModelV0_2
    sade.d04.models.envelope_context.EnvelopeContext
    sade.adaptive_emitter.normalizer.SourceRowNormalizer
Main Callers / Consumers:
    sade.adaptive_pipeline.pipeline.AdaptivePipeline
Important Assumptions:
    source rows are causally ordered and timestamps strictly increase.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No D03 execution
    - No stateful TradingEnvelope execution
    - No Price/Volume engine execution
Failure / Error Behavior:
    Raises RuntimeError for invalid observations, causal violations, or invalid
    terminal decisions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from collections import deque
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from sade.adaptive_emitter.normalizer import SourceRowNormalizer
from sade.d01.v02.model import D01V02Model
from sade.d02.v02.builder import build_return_shape
from sade.d04.envelope.capturability_model import CapturabilityModelV0_2
from sade.d04.models.envelope_context import EnvelopeContext

CONTEXT_LENGTH = 15
DECISIONS = ("BUY", "SELL", "HOLD")
DIRECTION_SIGN = {"UPWARD": 1, "DOWNWARD": -1, "FLAT": 0}


def canonical_sha256(value: Any) -> str:
    """Return deterministic SHA-256 for JSON-serializable values."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class DevelopmentObservationStream:
    """Historical development stream reader preserved for compatibility utilities."""

    def __init__(
        self,
        source_path: Path,
        first_physical_row: int,
        last_physical_row: int,
        reserve_start_utc: str,
    ) -> None:
        self._path = source_path
        self._first = first_physical_row
        self._last = last_physical_row
        self._reserve_start = datetime.fromisoformat(reserve_start_utc.replace("Z", "+00:00"))
        self._handle = source_path.open(newline="", encoding="utf-8")
        header = next(csv.reader([self._handle.readline()]))
        for _ in range(first_physical_row - 2):
            if not self._handle.readline():
                raise RuntimeError("development source ended before selected range")
        self._reader = csv.DictReader(self._handle, fieldnames=header)
        self._next_physical_row = first_physical_row
        self._last_timestamp: datetime | None = None
        self.rows_exposed = 0
        self.reserve_rows_accessed = 0

    def next_observation(self) -> tuple[int, dict[str, str]] | None:
        """Return next observation row with physical-row identity."""
        if self._next_physical_row > self._last:
            return None
        row = next(self._reader, None)
        if row is None:
            raise RuntimeError("development source ended within selected range")
        timestamp = datetime.fromisoformat(row["event_timestamp_utc"].replace("Z", "+00:00"))
        if timestamp >= self._reserve_start:
            self.reserve_rows_accessed += 1
            raise RuntimeError("reserve boundary reached by development reader")
        if self._last_timestamp is not None and timestamp <= self._last_timestamp:
            raise RuntimeError("non-monotonic development source")
        physical_row = self._next_physical_row
        self._next_physical_row += 1
        self._last_timestamp = timestamp
        self.rows_exposed += 1
        return physical_row, dict(row)

    def close(self) -> None:
        """Close source handle."""
        self._handle.close()


class AdaptiveEmitter:
    """Execute one-step adaptive processing on source rows.

    Args:
        entity_id: target source entity.
        rule_fingerprint: scientific rule identity.
        code_fingerprint: scientific implementation identity.
    """

    def __init__(self, entity_id: str, rule_fingerprint: str, code_fingerprint: str) -> None:
        self.entity_id = entity_id
        self.rule_fingerprint = rule_fingerprint
        self.code_fingerprint = code_fingerprint
        self.d01 = D01V02Model(entity_id=entity_id)
        self.normalizer = SourceRowNormalizer(entity_id=entity_id)
        self.capturability = CapturabilityModelV0_2()
        self.context: deque[dict[str, Any]] = deque(maxlen=CONTEXT_LENGTH)
        self.position_state = "FLAT"
        self.previous_decision: str | None = None
        self.completed_count = 0
        self.emissions: list[dict[str, Any]] = []
        self.initialization: list[dict[str, Any]] = []
        self.adaptation_audit: list[dict[str, Any]] = []
        self.feedback_audit: list[dict[str, Any]] = []
        self._last_source_time: float | None = None

    @staticmethod
    def _adaptive_properties(context: tuple[dict[str, Any], ...], current_c: float) -> dict[str, Any]:
        c_values = [item["C"] for item in context]
        signs = [DIRECTION_SIGN[item["path_direction"]] for item in context]
        return {
            "prior_15_median_C": median(c_values),
            "prior_15_min_C": min(c_values),
            "prior_15_max_C": max(c_values),
            "prior_15_range_C": max(c_values) - min(c_values),
            "prior_C": c_values[-1],
            "delta_C": current_c - c_values[-1],
            "up_count": sum(sign > 0 for sign in signs),
            "down_count": sum(sign < 0 for sign in signs),
            "flat_count": sum(sign == 0 for sign in signs),
            "direction_balance": sum(signs),
        }

    @staticmethod
    def _decide(path_direction: str, h: int, c_value: float, adaptive: dict[str, Any]) -> tuple[str, str]:
        quality_eligible = h == 1 and c_value >= adaptive["prior_15_median_C"]
        if path_direction == "UPWARD" and quality_eligible and adaptive["up_count"] >= adaptive["down_count"]:
            return "BUY", "UPWARD_AND_PRIOR_DIRECTION_AGREEMENT_AND_C_GE_PRIOR_MEDIAN"
        if path_direction == "DOWNWARD" and quality_eligible and adaptive["down_count"] >= adaptive["up_count"]:
            return "SELL", "DOWNWARD_AND_PRIOR_DIRECTION_AGREEMENT_AND_C_GE_PRIOR_MEDIAN"
        return "HOLD", "AFFIRM_POSITION_STATE_TRANSITION_PREDICATE_NOT_SATISFIED"

    def process(self, physical_row: int, source_row: dict[str, str]) -> dict[str, Any]:
        """Process one source row into an immutable adaptive emission.

        Args:
            physical_row: compatibility row identity expected by frozen seam.
            source_row: mapped source observation dictionary.

        Returns:
            Emission dictionary including scientific outputs and state transition.
        """
        lifecycle_start = time.perf_counter_ns()
        stage: dict[str, int] = {}

        started = time.perf_counter_ns()
        observation = self.normalizer.source_row_to_normalized_observation(source_row, physical_row - 2)
        stage["SOURCE_ADMISSION"] = time.perf_counter_ns() - started
        if observation is None:
            raise RuntimeError(f"INVALID source observation at physical row {physical_row}")
        delta_t = None if self._last_source_time is None else observation.event_time - self._last_source_time
        if delta_t is not None and delta_t <= 0:
            raise RuntimeError("source time must increase")

        state_before = {
            "completed_count": self.completed_count,
            "position_state": self.position_state,
            "previous_decision": self.previous_decision,
            "d01_state_hash": self.d01.state.state_hash if hasattr(self.d01.state, "state_hash") else canonical_sha256(asdict(self.d01.state)),
            "context_ids": [item["observation_id"] for item in self.context],
        }

        started = time.perf_counter_ns()
        dmo, fmo = self.d01.step(observation)
        stage["D01"] = time.perf_counter_ns() - started

        started = time.perf_counter_ns()
        shape = build_return_shape(dmo, fmo)
        stage["D02"] = time.perf_counter_ns() - started

        started = time.perf_counter_ns()
        capture = self.capturability.evaluate(shape, EnvelopeContext.production(evaluation_time=observation.event_time))
        stage["FOUR_FACTOR"] = time.perf_counter_ns() - started

        vector = {
            "H": capture.hard_eligibility,
            "Q_G": capture.geometry_quality,
            "Q_S": capture.structural_quality,
            "Q_R": capture.risk_quality,
            "C": capture.capturability_score,
        }
        observation_id = canonical_sha256(
            {
                "physical_row": physical_row,
                "source_row_number": source_row["source_row_number"],
                "timestamp": source_row["event_timestamp_utc"],
                "ohlcv": {name: source_row[name] for name in ("open", "high", "low", "close", "volume")},
            }
        )
        completed_record = {
            "observation_index": self.completed_count + 1,
            "observation_id": observation_id,
            "physical_row": physical_row,
            "source_timestamp": source_row["event_timestamp_utc"],
            "source": {name: float(source_row[name]) for name in ("open", "high", "low", "close", "volume")},
            "delta_t_seconds": delta_t,
            "path_direction": shape.path_direction.value,
            "terminal_displacement": shape.terminal_displacement,
            "state_velocity": dmo.state_velocity,
            "state_acceleration": dmo.state_acceleration,
            "strength": shape.strength,
            "coherence": shape.coherence,
            "persistence": shape.persistence,
            "uncertainty": shape.uncertainty,
            "reversal_propensity": shape.reversal_propensity,
            **vector,
        }

        if self.completed_count < CONTEXT_LENGTH:
            status = "INITIALIZING"
            decision = None
            rule_path = "INITIALIZATION_NON_ACTIONABLE"
            adaptive: dict[str, Any] = {}
            context_ids = [item["observation_id"] for item in self.context]
        else:
            if len(self.context) != CONTEXT_LENGTH:
                raise RuntimeError("actionable context length is not 15")
            status = "ACTIONABLE"
            context_snapshot = tuple(deepcopy(item) for item in self.context)
            context_ids = [item["observation_id"] for item in context_snapshot]
            started = time.perf_counter_ns()
            adaptive = self._adaptive_properties(context_snapshot, vector["C"])
            decision, rule_path = self._decide(shape.path_direction.value, vector["H"], vector["C"], adaptive)
            stage["ADAPTIVE_DECISION"] = time.perf_counter_ns() - started
            if decision not in DECISIONS:
                raise RuntimeError("terminal decision outside authority")

        old_position = self.position_state
        old_decision = self.previous_decision
        if decision == "BUY":
            next_position = "LONG"
        elif decision == "SELL":
            next_position = "SHORT"
        else:
            next_position = self.position_state

        lifecycle_end = time.perf_counter_ns()
        emission_core = {
            "observation_index": self.completed_count + 1,
            "observation_id": observation_id,
            "physical_row": physical_row,
            "observation_timestamp": source_row["event_timestamp_utc"],
            "prior_context_ids": context_ids,
            "context_start_timestamp": self.context[0]["source_timestamp"] if self.context else None,
            "context_end_timestamp": self.context[-1]["source_timestamp"] if self.context else None,
            "source_delta_t_seconds": delta_t,
            "status": status,
            "state_before": state_before,
            "mathematics": {"dmo": dmo.to_dict(), "fmo": fmo.to_dict(), "return_shape": shape.to_dict(), **vector},
            "adaptive_properties": adaptive,
            "position_state_before": old_position,
            "position_decision": decision,
            "decision_rule_path": rule_path,
            "feedback_generated": [] if decision is None else ["prior_decision", "position_state"],
            "state_after": {
                "completed_count": self.completed_count + 1,
                "position_state": next_position,
                "previous_decision": decision if decision is not None else old_decision,
            },
            "lifecycle_start_ns": lifecycle_start,
            "lifecycle_end_ns": lifecycle_end,
            "direct_lifecycle_ns": lifecycle_end - lifecycle_start,
            "component_lifecycle_ns": stage,
            "source_fingerprint": observation_id,
            "rule_fingerprint": self.rule_fingerprint,
            "code_fingerprint": self.code_fingerprint,
            "future_access_count": 0,
        }
        emission_id = canonical_sha256(emission_core)
        emission = {"emission_id": emission_id, **emission_core}
        emission_hash = canonical_sha256(emission)

        prior_adaptive = self._adaptive_properties(tuple(self.context), self.context[-1]["C"]) if len(self.context) == CONTEXT_LENGTH else None
        self.context.append(deepcopy(completed_record))
        if len(self.context) == CONTEXT_LENGTH:
            new_adaptive = self._adaptive_properties(tuple(self.context), self.context[-1]["C"])
            for name, new_value in new_adaptive.items():
                old_value = None if prior_adaptive is None else prior_adaptive[name]
                if old_value != new_value:
                    self.adaptation_audit.append(
                        {
                            "property": name,
                            "old_value": old_value,
                            "new_value": new_value,
                            "causal_observation_id": observation_id,
                            "rolling_context_ids": [item["observation_id"] for item in self.context],
                            "equation": "defined rolling-15 operator",
                            "timestamp": source_row["event_timestamp_utc"],
                            "effective_observation": self.completed_count + 2,
                        }
                    )
        if decision is not None:
            self.feedback_audit.extend(
                [
                    {
                        "source_emission_id": emission_id,
                        "feedback_property": "position_decision",
                        "target_state_property": "previous_decision",
                        "old_value": old_decision,
                        "new_value": decision,
                        "equation": "previous_decision_(n+1)=decision_n",
                        "timestamp": source_row["event_timestamp_utc"],
                        "effective_observation": self.completed_count + 2,
                    },
                    {
                        "source_emission_id": emission_id,
                        "feedback_property": "position_transition",
                        "target_state_property": "position_state",
                        "old_value": old_position,
                        "new_value": next_position,
                        "equation": "BUY->LONG; SELL->SHORT; HOLD->preserve",
                        "timestamp": source_row["event_timestamp_utc"],
                        "effective_observation": self.completed_count + 2,
                    },
                ]
            )
            self.position_state = next_position
            self.previous_decision = decision
            self.emissions.append(deepcopy(emission))
        else:
            self.initialization.append(deepcopy(emission))

        self.completed_count += 1
        self._last_source_time = observation.event_time
        if canonical_sha256(emission) != emission_hash:
            raise RuntimeError("emission mutated after persistence")
        return emission
