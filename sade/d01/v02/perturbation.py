from __future__ import annotations

import math

from sade.d01.v02.config import PerturbationConfig


PERTURBATION_NONE = "NONE"
PERTURBATION_REINFORCING = "REINFORCING"
PERTURBATION_CONTRADICTING = "CONTRADICTING"
PERTURBATION_REVERSING = "REVERSING"
PERTURBATION_STRUCTURAL = "STRUCTURAL/UNKNOWN"


def _direction(value: float, epsilon: float) -> int:
    if value > epsilon:
        return 1
    if value < -epsilon:
        return -1
    return 0


def infer_perturbation_class(
    innovation_residual: float,
    prior_level: float,
    prev_velocity: float,
    velocity: float,
    directional_epsilon: float = 1e-15,
) -> str:
    state_direction = _direction(prior_level, directional_epsilon)
    if state_direction == 0:
        state_direction = _direction(prev_velocity, directional_epsilon)

    evidence_direction = _direction(innovation_residual, directional_epsilon)
    if evidence_direction == 0:
        evidence_direction = _direction(velocity - prev_velocity, directional_epsilon)

    if state_direction == 0 or evidence_direction == 0:
        return PERTURBATION_STRUCTURAL

    current_direction = _direction(velocity, directional_epsilon)
    if evidence_direction == -state_direction:
        if current_direction == -state_direction:
            return PERTURBATION_REVERSING
        return PERTURBATION_CONTRADICTING
    if evidence_direction == state_direction:
        return PERTURBATION_REINFORCING
    return PERTURBATION_STRUCTURAL


def classify_perturbation(
    innovation: float,
    prev_velocity: float,
    velocity: float,
    source_quality: float,
    cfg: PerturbationConfig,
    numerical_epsilon: float = 1e-8,
    innovation_residual: float | None = None,
    prior_level: float = 0.0,
) -> tuple[str, float, float]:
    q = max(0.0, min(1.0, innovation / (1.0 + innovation)))
    lo, hi = cfg.adaptation_multiplier_bounds
    mag_multiplier = max(lo, min(hi, 1.0 + q * (hi - 1.0)))

    if source_quality < cfg.structural_quality_floor:
        return PERTURBATION_STRUCTURAL, q, mag_multiplier

    materiality_floor = math.sqrt(max(0.0, numerical_epsilon))
    if q <= materiality_floor:
        return PERTURBATION_NONE, q, mag_multiplier

    signed_evidence = innovation_residual
    if signed_evidence is None:
        signed_evidence = velocity - prev_velocity
    perturbation_class = infer_perturbation_class(
        innovation_residual=signed_evidence,
        prior_level=prior_level,
        prev_velocity=prev_velocity,
        velocity=velocity,
    )
    return perturbation_class, q, mag_multiplier

