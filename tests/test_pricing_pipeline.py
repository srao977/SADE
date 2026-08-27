"""
Module/File Name: tests/test_pricing_pipeline.py
Date Created / Modified: August 27, 2026
Purpose:
    Validate SADE pricing pipeline behavior and seam contracts.
Executive Overview:
    Tests warm-up, active-index derivative/F4 scheduling, analytic projection,
    PriceEmission generation, cockpit output, and hard failures.
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
    numpy, pytest, and sade.pricing_pipeline.
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

import numpy as np
import pytest

from sade.pricing_pipeline import PricingPipeline, PricingPipelineConfig
from sade.pricing_pipeline import pipeline as pipeline_module, projection
from sade.pricing_pipeline.derivatives import causal_quadratic, causal_quadratic_at_index
from sade.pricing_pipeline.dynamics import fit_f4, fit_f4_at_index


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


def test_production_pricing_does_not_invoke_rk45(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("production invoked RK45 reference")

    monkeypatch.setattr(projection, "solve_ivp", forbidden)
    monkeypatch.setattr(projection, "solve_cover_rk45_reference", forbidden)
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    ts = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    emitted = 0
    for i in range(100):
        if i > 0:
            ts += timedelta(seconds=60)
        step = pipeline.process(_record(i, ts, 100.0 + 0.05 * i + 0.8 * (i % 5)))
        emitted += step["price_emission"] is not None

    assert emitted > 0


def test_active_index_fits_are_bit_exact_to_full_history_references() -> None:
    times = np.cumsum(np.resize(np.asarray([1.0, 1.0, 5.0, 1.0]), 100))
    prices = 100.0 + np.sin(times / 7.0) + 0.01 * times * times
    p1, p2, failures = causal_quadratic(times, prices, 15)

    active_failures = 0
    for index in range(len(prices)):
        active_p1, active_p2, active_failure = causal_quadratic_at_index(times, prices, index, 15)
        assert np.asarray(active_p1).tobytes() == np.asarray(p1[index]).tobytes()
        assert np.asarray(active_p2).tobytes() == np.asarray(p2[index]).tobytes()
        active_failures += active_failure
    assert active_failures == failures

    jp = np.full(len(prices), np.nan)
    jp[1:] = p2[1:] - p2[:-1]
    reference_fit = fit_f4(prices, p1, p2, jp, 30)
    fit_fields = ("standardized", "physical", "means", "scales", "minimum", "maximum", "condition")
    for index in range(len(prices)):
        active_fit = fit_f4_at_index(prices, p1, p2, jp, index, 30)
        reference_available = bool(np.all(np.isfinite(reference_fit["standardized"][index])))
        assert (active_fit is not None) == reference_available
        if active_fit is not None:
            for field in fit_fields:
                assert np.asarray(active_fit[field]).tobytes() == np.asarray(reference_fit[field][index]).tobytes()


def test_production_fits_each_active_index_at_most_once(monkeypatch: pytest.MonkeyPatch) -> None:
    derivative_indices: list[int] = []
    f4_indices: list[int] = []
    derivative_reference = pipeline_module.causal_quadratic_at_index
    f4_reference = pipeline_module.fit_f4_at_index

    def counted_derivative(*args: object, **kwargs: object) -> tuple[float, float, int]:
        derivative_indices.append(int(args[2]))
        return derivative_reference(*args, **kwargs)

    def counted_f4(*args: object, **kwargs: object) -> dict[str, np.ndarray | float] | None:
        f4_indices.append(int(args[4]))
        return f4_reference(*args, **kwargs)

    monkeypatch.setattr(pipeline_module, "causal_quadratic_at_index", counted_derivative)
    monkeypatch.setattr(pipeline_module, "fit_f4_at_index", counted_f4)

    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    timestamp = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    observation_indices: list[int] = []
    for index in range(100):
        step = pipeline.process(_record(index, timestamp, 100.0 + 0.05 * index + 0.8 * (index % 5)))
        observation_indices.append(int(step["observation_index"]))
        timestamp += timedelta(seconds=60)

    assert derivative_indices == [*range(29), *([29] * 70)]
    assert f4_indices == [29] * 55
    assert observation_indices == [1, *range(1, 100)]


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


def test_pricing_histories_remain_at_scientific_bound_and_processing_continues() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    timestamp = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    emitted_after_bound = 0
    for index in range(500):
        step = pipeline.process(
            _record(index, timestamp, 100.0 + 0.05 * index + 0.8 * (index % 5))
        )
        if index >= 100 and step["price_emission"] is not None:
            emitted_after_bound += 1
        timestamp += timedelta(seconds=60)

    histories = (
        pipeline._timestamps,
        pipeline._times_minutes,
        pipeline._opens,
        pipeline._highs,
        pipeline._lows,
        pipeline._closes,
        pipeline._volumes,
        pipeline._p1,
        pipeline._p2,
        pipeline._jp,
    )
    assert pipeline._history_limit == 31
    assert all(len(history) == pipeline._history_limit for history in histories)
    assert pipeline._last_source_row_index == 499
    assert emitted_after_bound > 0


def test_pricing_instances_do_not_cross_contaminate_bounded_state() -> None:
    first = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    second = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    timestamp = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    for index in range(40):
        first.process(_record(index, timestamp, 100.0 + index))
        timestamp += timedelta(seconds=60)

    assert len(first._closes) == 31
    assert len(second._closes) == 0
    assert second._last_source_row_index is None
