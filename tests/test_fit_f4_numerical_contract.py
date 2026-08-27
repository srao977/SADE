"""
Module/File Name: tests/test_fit_f4_numerical_contract.py
Date Created / Modified: August 27, 2026
Purpose:
    Freeze fit_f4 numerical and downstream categorical semantics for Finding 004.
Scientific Mathematics Changed:
    NO
Standard Deviation:
    POPULATION
ddof:
    0
Normal Equations:
    PRESERVED
Condition Number:
    SCIENTIFICALLY DOWNSTREAM-RELEVANT
Go Migration:
    NOT IMPLEMENTED
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sade.pricing_pipeline.dynamics import allocate_fit, fit_f4_at_index, valid_fit
from sade.pricing_pipeline.pipeline import PricingPipeline, PricingPipelineConfig
from sade.pricing_pipeline.price_engine import CockpitState, PolicyState
from sade.unit_run.validate_finding_004 import decode_hex_array, replay_case


CORPUS = Path("output/python_prove/finding_004/fit_f4_golden_corpus.jsonl")
CONTRACT = Path("output/python_prove/finding_004/fit_f4_numerical_contract.json")


def _cases() -> list[dict[str, object]]:
    return [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]


def _assert_bits(actual: object, expected_hex: object) -> None:
    expected = decode_hex_array(expected_hex)
    assert np.asarray(actual, dtype=np.float64).tobytes() == expected.tobytes()


def test_golden_corpus_replays_every_fit_bit_exactly() -> None:
    cases = _cases()
    assert len(cases) == 55
    for case in cases:
        fit = replay_case(case)
        assert fit is not None
        for field in ("means", "scales", "standardized", "physical", "minimum", "maximum"):
            _assert_bits(fit[field], case["expected"][f"{field}_hex"])
        assert float(fit["condition"]).hex() == case["expected"]["condition_hex"]
        assert case["expected"]["valid_fit"] is True


def test_population_ddof_design_ridge_normal_equations_and_conversion_are_frozen() -> None:
    case = _cases()[0]
    inputs = case["inputs"]
    p, p1, p2, jp = (
        decode_hex_array(inputs[f"{name}_window_hex"])
        for name in ("p", "p1", "p2", "jp")
    )
    values = np.column_stack((p, p1, p2))
    means = values.mean(axis=0)
    scales = values.std(axis=0, ddof=0)
    standardized = (values - means) / scales
    design = np.column_stack((np.ones(30), standardized))
    ridge = np.diag([0.0, 1.0, 1.0, 1.0])
    normal_matrix = design.T @ design + ridge
    rhs = design.T @ jp
    beta = np.linalg.solve(normal_matrix, rhs)
    slopes = beta[1:] / scales
    physical = np.r_[beta[0] - slopes @ means, slopes]

    assert case["window_size"] == 30
    _assert_bits(means, case["intermediates"]["means_hex"])
    _assert_bits(scales, case["intermediates"]["population_scales_hex"])
    _assert_bits(standardized, case["intermediates"]["standardized_inputs_hex"])
    _assert_bits(design, case["intermediates"]["design_matrix_hex"])
    _assert_bits(ridge, case["intermediates"]["ridge_matrix_hex"])
    _assert_bits(normal_matrix, case["intermediates"]["normal_equation_matrix_hex"])
    _assert_bits(rhs, case["intermediates"]["normal_equation_rhs_hex"])
    _assert_bits(beta, case["expected"]["standardized_hex"])
    _assert_bits(physical, case["expected"]["physical_hex"])
    assert np.all(design[:, 0] == 1.0)
    assert np.all(np.diag(ridge) == np.asarray([0.0, 1.0, 1.0, 1.0]))
    assert np.linalg.cond(design).hex() == case["expected"]["condition_hex"]


def test_sample_standard_deviation_is_a_detectably_wrong_path() -> None:
    case = _cases()[0]
    values = decode_hex_array(case["intermediates"]["values_hex"])
    population = values.std(axis=0, ddof=0)
    sample = values.std(axis=0, ddof=1)
    assert not np.array_equal(population, sample)
    assert np.allclose(sample / population, np.sqrt(30.0 / 29.0), rtol=0.0, atol=1e-15)

    jp = decode_hex_array(case["inputs"]["jp_window_hex"])
    means = values.mean(axis=0)
    ridge = np.diag([0.0, 1.0, 1.0, 1.0])
    population_design = np.column_stack((np.ones(30), (values - means) / population))
    sample_design = np.column_stack((np.ones(30), (values - means) / sample))
    population_beta = np.linalg.solve(population_design.T @ population_design + ridge, population_design.T @ jp)
    sample_beta = np.linalg.solve(sample_design.T @ sample_design + ridge, sample_design.T @ jp)
    assert not np.array_equal(population_beta, sample_beta)
    assert np.linalg.cond(population_design) != np.linalg.cond(sample_design)


def test_valid_fit_contract_is_standardized_beta_finiteness() -> None:
    fit = allocate_fit(1, 4)
    assert valid_fit(fit, 0) is False
    fit["standardized"][0] = np.asarray([0.0, 1.0, 2.0, 3.0])
    assert valid_fit(fit, 0) is True
    fit["standardized"][0, 2] = np.inf
    assert valid_fit(fit, 0) is False


def test_condition_thresholds_are_exact_discrete_policy_boundaries() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL", enable_cockpit=False))
    policy = pipeline._policy
    base = {
        "symbol": "AAPL", "timestamp": "2026-08-27T00:00:00Z",
        "p": 100.0, "p1": 1.0, "p2": 1.0,
        "projected_p": 101.0, "projected_p1": 2.0, "projected_p2": 1.0,
        "rk_success": True, "domain_exit": False,
    }
    median = policy.config.condition_median
    q95 = policy.config.condition_q95
    median_companions = {"max_real_eigenvalue": 0.0, "perturbation_amplification": 1.0}
    q95_companions = {"max_real_eigenvalue": 0.5, "perturbation_amplification": 2.5}

    below_median, _ = policy.emit({**base, **median_companions, "condition_number": np.nextafter(median, -np.inf)}, PolicyState())
    above_median, _ = policy.emit({**base, **median_companions, "condition_number": np.nextafter(median, np.inf)}, PolicyState())
    below_q95, _ = policy.emit({**base, **q95_companions, "condition_number": np.nextafter(q95, -np.inf)}, PolicyState())
    above_q95, _ = policy.emit({**base, **q95_companions, "condition_number": np.nextafter(q95, np.inf)}, PolicyState())
    assert (below_median.confidence_state, above_median.confidence_state) == ("HIGH", "MEDIUM")
    assert (below_q95.confidence_state, above_q95.confidence_state) == ("MEDIUM", "LOW")


def test_corpus_downstream_categories_replay_exactly_in_source_order() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    policy_state = PolicyState()
    cockpit_state = CockpitState()
    for case in _cases():
        source = case["source_identity"]
        encoded = case["downstream"]["policy_inputs"]
        numerical = {
            "symbol": source["entity"],
            "timestamp": source["source_timestamp"],
            **{name: float.fromhex(encoded[f"{name}_hex"]) for name in ("p", "p1", "p2", "projected_p", "projected_p1", "projected_p2", "condition_number", "max_real_eigenvalue", "perturbation_amplification")},
            "rk_success": encoded["rk_success"],
            "domain_exit": encoded["domain_exit"],
        }
        emission, policy_state = pipeline._policy.emit(numerical, policy_state)
        actual_emission = emission.as_dict()
        for field, expected in case["downstream"]["price_emission"].items():
            assert actual_emission[field] == expected
        cockpit, cockpit_state = pipeline._cockpit.observe(emission, cockpit_state)
        actual_cockpit = cockpit.as_dict()
        for field, expected in case["downstream"]["cockpit"].items():
            assert actual_cockpit[field] == expected


def test_contract_metadata_freezes_condition_matrix_and_threshold_consumers() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["standard_deviation"]["ddof"] == 0
    assert contract["condition_number"]["input_matrix"] == "design"
    assert contract["ridge"]["intercept_penalized"] is False
    assert [item["threshold"] for item in contract["downstream_condition_consumers"]] == [
        7.835779770603297,
        13.040323846425492,
    ]


def test_finding_003_pricing_bound_remains_derived_from_f4_window() -> None:
    pipeline = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    assert pipeline.config.f4_window == 30
    assert pipeline._history_limit == 31