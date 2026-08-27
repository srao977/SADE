"""
Module/File Name: tests/test_pricing_migration_equivalence.py
Date Created / Migrated: August 25, 2026
Purpose:
    Prove migrated pricing mathematics and PriceEngine behavior match APTF source.
Executive Overview:
    Loads APTF source implementations as authority and compares outputs against
    SADE migrated implementations using fixed deterministic fixtures.
Role in SADE:
    Migration-science equivalence gate.
Inputs:
    Synthetic deterministic fixture arrays.
Outputs:
    Pytest equivalence assertions.
Parameters / Configuration:
    Uses APTF source paths under C:/Users/chino/APTF.
Persistent State:
    None.
External Dependencies:
    numpy, pytest, and scipy.
Main Callers / Consumers:
    Migration validation workflow.
Important Assumptions:
    APTF source repository is available at the declared path for equivalence tests.
Scientific Provenance:
    Compares against:
    - diagnostics/run_test_009_derivative_analysis.py
    - diagnostics/run_test_013b_qqq_validation.py
    - diagnostics/run_test_014_policy_development.py::build_numerical
    - price_engine package
Explicit Exclusions / What This Module Does NOT Do:
    - No live SDX calls
    - No runtime dependency in production pricing pipeline
Failure / Error Behavior:
    Test is skipped if APTF source path is unavailable.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from sade.pricing_pipeline.derivatives import causal_quadratic
from sade.pricing_pipeline.dynamics import fit_f4
from sade.pricing_pipeline.numerical import build_numerical_row
from sade.pricing_pipeline.price_engine import (
    CockpitPolicyConfig,
    CockpitState,
    EmissionPolicy,
    MarketObservation,
    PolicyConfig,
    PolicyState,
    PriceCockpitInterpreter,
    PriceEngine,
)
from sade.pricing_pipeline.projection import solve_cover, solve_cover_rk45_reference


APTF_ROOT = Path("C:/Users/chino/APTF")


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def aptf_modules():
    if not APTF_ROOT.exists():
        pytest.skip("APTF source path not available for migration equivalence test")

    deriv = _load_module(APTF_ROOT / "diagnostics" / "run_test_009_derivative_analysis.py", "aptf_test009")
    val13b = _load_module(APTF_ROOT / "diagnostics" / "run_test_013b_qqq_validation.py", "aptf_test013b")

    sys.path.insert(0, str(APTF_ROOT))
    sys.path.insert(0, str(APTF_ROOT / "diagnostics"))
    import price_engine as aptf_price_engine  # type: ignore
    from price_engine.cockpit import (  # type: ignore
        CockpitPolicyConfig as AptfCockpitPolicyConfig,
        CockpitState as AptfCockpitState,
        PriceCockpitInterpreter as AptfPriceCockpitInterpreter,
    )

    dev14 = _load_module(APTF_ROOT / "diagnostics" / "run_test_014_policy_development.py", "aptf_test014")
    return deriv, val13b, aptf_price_engine, dev14, AptfCockpitPolicyConfig, AptfCockpitState, AptfPriceCockpitInterpreter


def _fixture_series(n: int = 90):
    base = datetime(2026, 8, 25, 13, 30, tzinfo=timezone.utc)
    ts = [base + timedelta(seconds=60 * i + (30 if i % 11 == 0 else 0)) for i in range(n)]
    tm = np.asarray([x.timestamp() / 60.0 for x in ts], dtype=float)
    p = np.asarray([100.0 + 0.2 * i + 1.5 * np.sin(i / 5.0) for i in range(n)], dtype=float)
    return ts, tm, p


def test_causal_quadratic_equivalence(aptf_modules) -> None:
    deriv, *_ = aptf_modules
    _ts, tm, p = _fixture_series()
    d1_a, d2_a, f_a = deriv.causal_quadratic(tm, p, 15)
    d1_s, d2_s, f_s = causal_quadratic(tm, p, 15)
    np.testing.assert_allclose(d1_s, d1_a, equal_nan=True)
    np.testing.assert_allclose(d2_s, d2_a, equal_nan=True)
    assert f_s == f_a


def test_f4_and_rk45_reference_equivalence(aptf_modules) -> None:
    deriv, val13b, *_ = aptf_modules
    _ts, tm, p = _fixture_series()
    p1, p2, _ = deriv.causal_quadratic(tm, p, 15)
    jp = np.full(len(p), np.nan)
    for i in range(1, len(p)):
        if np.isfinite(p2[i - 1]) and np.isfinite(p2[i]):
            jp[i] = p2[i] - p2[i - 1]

    fit_a = val13b.fit_f4(p, p1, p2, jp, 30)
    fit_s = fit_f4(p, p1, p2, jp, 30, 1.0)

    idx = next(i for i in range(40, len(p) - 2) if np.all(np.isfinite(fit_a["standardized"][i])))
    np.testing.assert_allclose(fit_s["standardized"][idx], fit_a["standardized"][idx])
    np.testing.assert_allclose(fit_s["physical"][idx], fit_a["physical"][idx])
    np.testing.assert_allclose(fit_s["means"][idx], fit_a["means"][idx])
    np.testing.assert_allclose(fit_s["scales"][idx], fit_a["scales"][idx])

    solved_a, failed_a = val13b.solve_cover([idx], fit_a, p, p1, p2, False)
    solved_s, failed_s = solve_cover_rk45_reference(
        [idx], fit_s, p, p1, p2, False, val13b.RTOL, val13b.EPSILON
    )
    assert failed_s == failed_a
    np.testing.assert_allclose(solved_s[idx]["trajectory"], solved_a[idx]["trajectory"])

    solved_analytic, failed_analytic = solve_cover(
        [idx], fit_s, p, p1, p2, False, val13b.RTOL, val13b.EPSILON
    )
    assert failed_analytic == failed_a
    np.testing.assert_allclose(
        solved_analytic[idx]["trajectory"],
        solved_a[idx]["trajectory"],
        rtol=1e-6,
        atol=1e-8,
    )


def test_numerical_and_price_engine_equivalence(aptf_modules) -> None:
    deriv, val13b, aptf_price_engine, dev14, AptfCockpitPolicyConfig, AptfCockpitState, AptfPriceCockpitInterpreter = aptf_modules
    ts, tm, p = _fixture_series()
    p1, p2, _ = deriv.causal_quadratic(tm, p, 15)
    jp = np.full(len(p), np.nan)
    for i in range(1, len(p)):
        if np.isfinite(p2[i - 1]) and np.isfinite(p2[i]):
            jp[i] = p2[i] - p2[i - 1]

    fit = fit_f4(p, p1, p2, jp, 30, 1.0)
    idx = next(i for i in range(40, len(p) - 2) if np.all(np.isfinite(fit["standardized"][i])))
    solved_s, failed_s = solve_cover([idx], fit, p, p1, p2, False, 1e-6, 0.0035332071428566536)

    price_rows = [{"timestamp": t.isoformat().replace("+00:00", "Z"), "price": str(v), "primary_D1": str(p1i), "primary_D2": str(p2i)} for t, v, p1i, p2i in zip(ts, p, p1, p2)]
    source_rows = [{"event_timestamp_utc": t.isoformat().replace("+00:00", "Z"), "session_type": "UNKNOWN", "open": str(v - 0.1), "high": str(v + 0.2), "low": str(v - 0.2), "close": str(v), "volume": "1000", "source_provider": "SDX_TEST"} for t, v in zip(ts, p)]

    aptf_numerical = dev14.build_numerical([idx + 1], fit, solved_s, failed_s, price_rows, source_rows, p, p1, p2)[0]
    sade_numerical = build_numerical_row(
        index=idx,
        entity="AAPL",
        timestamp=price_rows[idx]["timestamp"],
        session="UNKNOWN",
        open_value=float(source_rows[idx]["open"]),
        high_value=float(source_rows[idx]["high"]),
        low_value=float(source_rows[idx]["low"]),
        close_value=float(source_rows[idx]["close"]),
        volume_value=float(source_rows[idx]["volume"]),
        source_provider=source_rows[idx]["source_provider"],
        fit=fit,
        solved=solved_s,
        failed=failed_s,
        p=p,
        p1=p1,
        p2=p2,
    )

    for key in (
        "p",
        "p1",
        "p2",
        "projected_p",
        "projected_p1",
        "projected_p2",
        "condition_number",
        "max_real_eigenvalue",
        "perturbation_amplification",
        "rk_success",
        "domain_exit",
    ):
        if isinstance(sade_numerical[key], float):
            assert sade_numerical[key] == pytest.approx(aptf_numerical[key])
        else:
            assert sade_numerical[key] == aptf_numerical[key]

    cfg = PolicyConfig(
        policy_id="P_EMISSION_V0_1",
        epsilon=0.0035332071428566536,
        condition_median=7.835779770603297,
        condition_q95=13.040323846425492,
        eigenvalue_median=0.42217565243576405,
        eigenvalue_q95=0.6449378901835623,
        amplification_median=2.2423650649621742,
        amplification_q95=2.6637448484678754,
        direct_reversal_debounce=True,
    )

    aptf_policy = aptf_price_engine.EmissionPolicy(
        aptf_price_engine.PolicyConfig(
            policy_id=cfg.policy_id,
            epsilon=cfg.epsilon,
            condition_median=cfg.condition_median,
            condition_q95=cfg.condition_q95,
            eigenvalue_median=cfg.eigenvalue_median,
            eigenvalue_q95=cfg.eigenvalue_q95,
            amplification_median=cfg.amplification_median,
            amplification_q95=cfg.amplification_q95,
            direct_reversal_debounce=cfg.direct_reversal_debounce,
        )
    )
    sade_policy = EmissionPolicy(cfg)

    aptf_engine = aptf_price_engine.PriceEngine(aptf_policy)
    sade_engine = PriceEngine(sade_policy)

    aptf_obs = aptf_price_engine.MarketObservation(
        symbol="AAPL",
        timestamp=sade_numerical["timestamp"],
        open=sade_numerical["open"],
        high=sade_numerical["high"],
        low=sade_numerical["low"],
        close=sade_numerical["close"],
        volume=sade_numerical["volume"],
        session="UNKNOWN",
        source="SDX_TEST",
    )
    sade_obs = MarketObservation(
        symbol="AAPL",
        timestamp=sade_numerical["timestamp"],
        open=sade_numerical["open"],
        high=sade_numerical["high"],
        low=sade_numerical["low"],
        close=sade_numerical["close"],
        volume=sade_numerical["volume"],
        session="UNKNOWN",
        source="SDX_TEST",
    )

    aptf_emission, aptf_state = aptf_engine.observe(aptf_obs, sade_numerical, aptf_price_engine.PolicyState())
    sade_emission, sade_state = sade_engine.observe(sade_obs, sade_numerical, PolicyState())

    assert sade_emission.as_dict() == aptf_emission.as_dict()
    assert sade_state.previous_color == aptf_state.previous_color
    assert sade_state.pending_reversal == aptf_state.pending_reversal

    aptf_cockpit = AptfPriceCockpitInterpreter(
        AptfCockpitPolicyConfig(
            policy_id="TRANSITION_EVIDENCE_P1",
            epsilon=0.0035332071428566536,
            zero_proximity_threshold=0.9,
            deceleration_strength_threshold=0.05,
            persistence_observations=1,
            candidate_hold_observations=0,
            low_confidence_requires_amber=False,
            domain_exit_requires_amber=False,
        )
    )
    sade_cockpit = PriceCockpitInterpreter(
        CockpitPolicyConfig(
            policy_id="TRANSITION_EVIDENCE_P1",
            epsilon=0.0035332071428566536,
            zero_proximity_threshold=0.9,
            deceleration_strength_threshold=0.05,
            persistence_observations=1,
            candidate_hold_observations=0,
            low_confidence_requires_amber=False,
            domain_exit_requires_amber=False,
        )
    )

    aptf_c_emit, aptf_c_state = aptf_cockpit.observe(aptf_emission, AptfCockpitState())
    sade_c_emit, sade_c_state = sade_cockpit.observe(sade_emission, CockpitState())
    assert sade_c_emit.as_dict() == aptf_c_emit.as_dict()
    assert sade_c_state.previous_color == aptf_c_state.previous_color
    assert sade_c_state.candidate_age == aptf_c_state.candidate_age
