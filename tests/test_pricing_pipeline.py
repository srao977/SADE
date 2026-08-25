"""
Module/File Name: tests/test_pricing_pipeline.py
Date Created / Migrated: August 25, 2026
Purpose:
    Validate SADE pricing pipeline behavior and seam contracts.
Executive Overview:
    Tests warm-up, derivative/F4 readiness, RK45 integration path, PriceEmission
    generation, cockpit output, irregular timestamp acceptance, and hard failures.
Role in SADE:
    Package tests for sade.pricing_pipeline.
Inputs:
    Synthetic adaptive-output-like records.
Outputs:
    Pytest pass/fail assertions.
Parameters / Configuration:
    PricingPipelineConfig.
Persistent State:
    Test-local pipeline instances.
External Dependencies:
    pytest and sade.pricing_pipeline.
Main Callers / Consumers:
    CI/manual package validation.
Important Assumptions:
    Tests are deterministic and do not require SDX.
Scientific Provenance:
    Verifies migrated Price mathematics orchestration behavior.
Explicit Exclusions / What This Module Does NOT Do:
    - No live SDX calls
    - No volume path tests
Failure / Error Behavior:
    Assertion failures indicate behavior regressions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sade.pricing_pipeline import PricingPipeline, PricingPipelineConfig


def _record(i: int, ts: datetime, close_value: float) -> dict[str, object]:
    return {
        "entity_id": "AAPL",
        "source_row_index": i,
        "source_timestamp": ts.isoformat().replace("+00:00", "Z"),
        "open": close_value - 0.1,
        "high": close_value + 0.2,
        "low": close_value - 0.2,
        "close": close_value,
        "volume": 1000 + i,
        "session_type": "UNKNOWN",
        "source_provider": "SDX_TEST",
    }


def test_pricing_pipeline_emits_after_warmup() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))

    ts = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    emitted = 0
    for i in range(180):
        if i > 0:
            ts = ts + timedelta(seconds=60)
        close_value = 100.0 + 0.05 * i + 0.8 * (i % 5)
        step = pipeline.process(_record(i, ts, close_value))
        if step["price_emission"] is not None:
            emitted += 1

    summary = pipeline.close()
    assert summary["observations_received"] == 180
    assert summary["warmup_observations"] > 0
    assert summary["derivative_ready_observations"] > 0
    assert summary["f4_ready_observations"] > 0
    assert summary["rk45_attempts"] > 0
    assert summary["price_emissions_generated"] == emitted
    assert summary["price_cockpit_outputs"] == emitted


def test_irregular_timestamps_are_accepted_without_cadence_checks() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    ts = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    for i in range(35):
        if i > 0:
            ts = ts + timedelta(seconds=120 if i % 6 == 0 else 60)
        pipeline.process(_record(i, ts, 100.0 + i * 0.1))
    summary = pipeline.close()
    assert summary["observations_received"] == 35


def test_missing_fields_fail_explicitly() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    with pytest.raises(ValueError, match="MISSING_ADAPTIVE_FIELD"):
        pipeline.process({"entity_id": "AAPL"})


def test_entity_mismatch_fails_explicitly() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    ts = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    row = _record(0, ts, 100.0)
    row["entity_id"] = "MSFT"
    with pytest.raises(ValueError, match="ENTITY_MISMATCH"):
        pipeline.process(row)


def test_row_order_regression_fails_explicitly() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    ts = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    pipeline.process(_record(0, ts, 100.0))
    with pytest.raises(ValueError, match="SOURCE_ORDER_REGRESSION"):
        pipeline.process(_record(0, ts + timedelta(seconds=60), 101.0))
