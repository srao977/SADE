"""
Module/File Name: tests/test_true_ingress_time.py
Date Created / Modified: August 27, 2026
Purpose:
    Validate true SADE ingress timestamps and local elapsed-time telemetry.
Event/Source Time:
    Scientific/provenance timestamp.
Receive/Ingress Time:
    Operational runtime timestamp.
Clock:
    UTC wall clock plus time.perf_counter_ns().
Scientific Mathematics Changed:
    NO
Scientific Model Uses Receive Time:
    NO
Latency Telemetry:
    OPERATIONAL ONLY
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sade.adaptive_emitter import AdaptiveEmitter
from sade.adaptive_emitter.normalizer import SourceRowNormalizer
from sade.adaptive_pipeline import pipeline as pipeline_module
from sade.adaptive_pipeline.pipeline import AdaptivePipeline, AdaptivePipelineConfig, build_source_row


class _Client:
    def close(self) -> None:
        pass


def _vector(index: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        entity_id="AAPL",
        source_row_index=index,
        source_timestamp="2000-01-01T00:00:00Z",
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000,
    )


def test_true_receive_time_is_independent_utc_and_source_time_is_preserved() -> None:
    receive_time = "2026-08-27T19:15:30.123456Z"
    row = build_source_row(_vector(), receive_time_utc=receive_time)
    observation = SourceRowNormalizer("AAPL").source_row_to_normalized_observation(row, 0)
    assert observation is not None
    assert row["event_timestamp_utc"] == "2000-01-01T00:00:00Z"
    assert row["receive_time_utc"] == receive_time
    assert observation.event_time == 946684800.0
    assert observation.receive_time == datetime.fromisoformat(receive_time.replace("Z", "+00:00")).timestamp()
    assert observation.receive_time != observation.event_time
    assert datetime.fromisoformat(receive_time.replace("Z", "+00:00")).tzinfo == timezone.utc


def test_direct_normalizer_call_captures_real_time_instead_of_event_time() -> None:
    before = datetime.now(timezone.utc).timestamp()
    observation = SourceRowNormalizer("AAPL").source_row_to_normalized_observation(
        {"event_timestamp_utc": "2000-01-01T00:00:00Z", "close": "100", "volume": "1"},
        0,
    )
    after = datetime.now(timezone.utc).timestamp()
    assert observation is not None
    assert before <= observation.receive_time <= after
    assert observation.receive_time != observation.event_time


def test_ingress_time_is_captured_once_and_not_overwritten(monkeypatch) -> None:
    wall_times = iter(("2026-08-27T19:15:30.123456Z", "2026-08-27T19:15:30.123789Z"))
    monotonic_ticks = iter((1_000_000, 1_000_400))
    monkeypatch.setattr(pipeline_module, "_utc_now_iso", lambda: next(wall_times))
    monkeypatch.setattr(pipeline_module, "_perf_counter_ns", lambda: next(monotonic_ticks))
    pipeline = AdaptivePipeline(AdaptivePipelineConfig(entity="AAPL", max_vectors=1), client=_Client())

    record = pipeline.process_vector(_vector())

    assert record["source_timestamp"] == "2000-01-01T00:00:00Z"
    assert record["receive_time_utc"] == "2026-08-27T19:15:30.123456Z"
    assert record["processing_complete_time_utc"] == "2026-08-27T19:15:30.123789Z"
    assert record["receive_monotonic_ns"] == 1_000_000
    assert record["ingress_to_adaptive_output_elapsed_ns"] == 400


def test_receive_time_does_not_change_observation_identity_or_science() -> None:
    first_row = build_source_row(_vector(), receive_time_utc="2026-08-27T19:00:00.000001Z")
    second_row = build_source_row(_vector(), receive_time_utc="2026-08-27T20:00:00.000001Z")
    first = AdaptiveEmitter("AAPL", "rule", "code").process(2, first_row)
    second = AdaptiveEmitter("AAPL", "rule", "code").process(2, second_row)

    assert first["observation_id"] == second["observation_id"]
    assert first["observation_timestamp"] == second["observation_timestamp"]
    assert first["mathematics"] == second["mathematics"]
    assert first["state_after"] == second["state_after"]
    assert first["decision_rule_path"] == second["decision_rule_path"]


def test_production_timing_state_is_constant_size() -> None:
    pipeline = AdaptivePipeline(AdaptivePipelineConfig(entity="AAPL", max_vectors=1), client=_Client())
    record = pipeline.process_vector(_vector())
    assert record["ingress_to_adaptive_output_elapsed_ns"] >= 0
    assert pipeline._rows == []
    assert not any("latency" in name or "receive_time" in name for name in vars(pipeline))


def test_runtime_timing_contract_defines_real_clock_endpoints() -> None:
    contract = json.loads(
        Path("output/python_prove/finding_005/runtime_timing_contract.json").read_text(encoding="utf-8")
    )
    adaptive = contract["metrics"]["ingress_to_adaptive_output_elapsed_ns"]
    pricing = contract["metrics"]["ingress_to_pricing_output_elapsed_ns"]
    assert contract["receive_time"]["clock"] == "datetime.now(timezone.utc)"
    assert contract["receive_time"]["capture_count"] == 1
    assert adaptive["clock"] == pricing["clock"] == "time.perf_counter_ns"
    assert adaptive["unit"] == pricing["unit"] == "nanoseconds"
    assert adaptive["start"] == "process_vector entry after gRPC iterator yields vector"
    assert "PriceEngine" in contract["excluded_scientific_uses"]