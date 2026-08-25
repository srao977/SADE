"""
Module/File Name: tests/test_sade_pipeline.py
Date Created / Migrated: August 25, 2026
Purpose:
    Validate SADE adaptive pipeline behavior and independence constraints.
Executive Overview:
    Focused tests verify mapping, ordering, failure propagation, serialization,
    and that core SADE imports resolve from SADE paths.
Role in SADE:
    Code-level package test suite for V0.1.
Inputs:
    Synthetic vectors and fake client/emitter stubs.
Outputs:
    Pytest pass/fail assertions.
Parameters / Configuration:
    AdaptivePipelineConfig values under test.
Persistent State:
    Local fake client/emitter state in test scope.
External Dependencies:
    pytest, sade package modules.
Main Callers / Consumers:
    CI/manual verification.
Important Assumptions:
    Tests do not replace live SDX unit-run validation.
Scientific Provenance:
    Tests verify orchestration around frozen adaptive lineage behavior.
Explicit Exclusions / What This Module Does NOT Do:
    - No scientific model re-validation math proof
    - No external network calls
Failure / Error Behavior:
    Assertion failures indicate behavioral regressions.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from sade.adaptive_pipeline.pipeline import AdaptivePipeline, AdaptivePipelineConfig, build_source_row, physical_row_from_source_index


class FakeClient:
    def __init__(self, vectors):
        self._vectors = list(vectors)
        self.closed = False

    def stream_vectors(self, entities, max_vectors_per_entity, timeout_seconds):
        _ = entities, max_vectors_per_entity, timeout_seconds
        for vector in self._vectors:
            yield vector

    def close(self):
        self.closed = True


class FakeEmitter:
    def __init__(self, fail: bool = False):
        self.adaptation_audit = []
        self.feedback_audit = []
        self.calls = 0
        self.fail = fail

    def process(self, physical_row, source_row):
        _ = physical_row, source_row
        if self.fail:
            raise RuntimeError("synthetic failure")
        self.calls += 1
        self.adaptation_audit.append({"n": self.calls})
        self.feedback_audit.extend([{"n": self.calls, "k": "decision"}, {"n": self.calls, "k": "state"}])
        status = "INITIALIZING" if self.calls <= 2 else "ACTIONABLE"
        decision = None if status == "INITIALIZING" else "HOLD"
        return {
            "status": status,
            "observation_id": f"obs_{self.calls}",
            "emission_id": f"em_{self.calls}",
            "source_delta_t_seconds": None if self.calls == 1 else 60.0,
            "decision_rule_path": "INITIALIZATION_NON_ACTIONABLE" if decision is None else "AFFIRM",
            "position_decision": decision,
            "position_state_before": "FLAT",
            "state_after": {"position_state": "FLAT"},
            "prior_context_ids": ["x"] * min(15, self.calls - 1),
            "mathematics": {
                "H": 1,
                "Q_G": 0.5,
                "Q_S": 0.5,
                "Q_R": 0.5,
                "C": 0.5,
                "return_shape": {
                    "path_direction": "UPWARD",
                    "terminal_displacement": 0.1,
                    "strength": 0.2,
                    "coherence": 0.3,
                    "persistence": 0.4,
                    "uncertainty": 0.5,
                    "reversal_propensity": 0.6,
                },
            },
        }


def _vector(index: int, entity: str = "AAPL", ts: str | None = None):
    return SimpleNamespace(
        entity_id=entity,
        source_row_index=index,
        source_timestamp=ts or f"2022-09-30 04:{index:02d}:00",
        open=100.0 + index,
        high=101.0 + index,
        low=99.0 + index,
        close=100.5 + index,
        volume=1000 + index,
    )


def test_package_import_path_is_sade_owned() -> None:
    import sade

    module_path = str(Path(sade.__file__).resolve()).lower()
    assert "\\sade\\" in module_path
    assert "\\aptf\\" not in module_path


def test_source_mapping_and_assumptions() -> None:
    row = build_source_row(_vector(7))
    assert row["source_row_number"] == "7"
    assert row["event_timestamp_utc"] == "2022-09-30 04:07:00"
    assert row["data_valid"] == "true"
    assert row["session_type"] == "UNKNOWN"


def test_physical_row_compatibility_mapping() -> None:
    assert physical_row_from_source_index(0) == 2
    assert physical_row_from_source_index(99) == 101


def test_entity_and_order_validation() -> None:
    pipeline = AdaptivePipeline(
        AdaptivePipelineConfig(entity="AAPL", max_vectors=2),
        client=FakeClient([]),
        emitter=FakeEmitter(),
    )
    pipeline.process_vector(_vector(0))
    with pytest.raises(ValueError, match="ROW_ORDER_REGRESSION"):
        pipeline.process_vector(_vector(0))
    with pytest.raises(ValueError, match="ENTITY_MISMATCH"):
        pipeline.process_vector(_vector(1, entity="MSFT"))


def test_malformed_vector_failure() -> None:
    pipeline = AdaptivePipeline(
        AdaptivePipelineConfig(max_vectors=1),
        client=FakeClient([]),
        emitter=FakeEmitter(),
    )
    with pytest.raises(AttributeError, match="MALFORMED_MARKETVECTOR"):
        pipeline.process_vector(SimpleNamespace(entity_id="AAPL"))


def test_short_stream_failure_and_summary_status(tmp_path: Path) -> None:
    pipeline = AdaptivePipeline(
        AdaptivePipelineConfig(max_vectors=3, output_dir=tmp_path),
        client=FakeClient([_vector(0), _vector(1)]),
        emitter=FakeEmitter(),
    )
    summary = pipeline.run()
    assert summary["status"] == "FAILED"
    assert "SHORT_STREAM" in "\n".join(summary["failures"])


def test_output_serialization_and_close(tmp_path: Path) -> None:
    client = FakeClient([_vector(0), _vector(1), _vector(2)])
    pipeline = AdaptivePipeline(
        AdaptivePipelineConfig(max_vectors=3, output_dir=tmp_path),
        client=client,
        emitter=FakeEmitter(),
    )
    summary = pipeline.run()
    assert summary["status"] == "COMPLETE"
    assert summary["vectors_received"] == 3
    assert (tmp_path / "observations.csv").exists()
    assert (tmp_path / "summary.json").exists()
    pipeline.close()
    assert client.closed is True


def test_emitter_failure_is_explicit() -> None:
    pipeline = AdaptivePipeline(
        AdaptivePipelineConfig(max_vectors=1),
        client=FakeClient([]),
        emitter=FakeEmitter(fail=True),
    )
    with pytest.raises(RuntimeError, match="ADAPTIVE_PROCESSING_FAILURE"):
        pipeline.process_vector(_vector(0))
