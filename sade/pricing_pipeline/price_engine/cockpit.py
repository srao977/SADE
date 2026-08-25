"""
Module/File Name: sade/pricing_pipeline/price_engine/cockpit.py
Date Created / Migrated: August 25, 2026
Purpose:
    Interpret PriceEmission into refined cockpit state/color diagnostics.
Executive Overview:
    Applies persistence and candidate-turn logic over PriceEmission derivatives to
    emit PriceCockpitEmission and next CockpitState.
Role in SADE:
    Post-policy interpreter that remains downstream of PriceEmission.
Inputs:
    PriceEmission and prior CockpitState.
Outputs:
    PriceCockpitEmission and next CockpitState.
Parameters / Configuration:
    CockpitPolicyConfig thresholds and persistence controls.
Persistent State:
    CockpitState is maintained externally by caller.
External Dependencies:
    sade.pricing_pipeline.price_engine.contracts.PriceEmission.
Main Callers / Consumers:
    sade.pricing_pipeline.pipeline and tests.
Important Assumptions:
    Emissions are causally ordered per stream partition.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF price_engine/cockpit.py
Explicit Exclusions / What This Module Does NOT Do:
    - No RK45 or F4 computation
    - No final execution BUY/HOLD/SELL generation
Failure / Error Behavior:
    Returns INVALID cockpit emission on rk/non-finite failures and raises ValueError
    for invalid configuration.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .contracts import PriceEmission


@dataclass(frozen=True)
class CockpitPolicyConfig:
    policy_id: str
    epsilon: float
    zero_proximity_threshold: float
    deceleration_strength_threshold: float
    persistence_observations: int
    candidate_hold_observations: int
    low_confidence_requires_amber: bool
    domain_exit_requires_amber: bool


@dataclass(frozen=True)
class CockpitState:
    previous_motion_state: str | None = None
    previous_color: str | None = None
    opposing_direction: str | None = None
    opposing_count: int = 0
    candidate_direction: str | None = None
    candidate_age: int = 0


@dataclass(frozen=True)
class PriceCockpitEmission:
    symbol: str
    timestamp: str
    engine: str
    raw_phase: str
    refined_internal_state: str
    p1_zero_proximity: float
    deceleration_strength: float
    persistence_state: str
    persistence_count: int
    turn_candidate: str
    candidate_age: int
    domain_state: str
    confidence_state: str
    raw_direction: str
    cockpit_color: str
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


class PriceCockpitInterpreter:
    """Refine PriceEmission into cockpit diagnostics and next CockpitState.

    Original APTF Source:
        price_engine/cockpit.py::PriceCockpitInterpreter
    Scientific Mathematics Changed:
        NO
    """

    def __init__(self, config: CockpitPolicyConfig):
        if config.epsilon <= 0:
            raise ValueError("epsilon must be positive")
        if config.persistence_observations < 1:
            raise ValueError("persistence_observations must be positive")
        if config.candidate_hold_observations < 0:
            raise ValueError("candidate_hold_observations cannot be negative")
        self.config = config

    def observe(
        self,
        emission: PriceEmission,
        state: CockpitState,
    ) -> tuple[PriceCockpitEmission, CockpitState]:
        values = (
            emission.p,
            emission.p1,
            emission.p2,
            emission.projected_p,
            emission.projected_p1,
            emission.projected_p2,
        )
        if not emission.rk_success or not all(math.isfinite(value) for value in values):
            output = self._build_invalid(emission)
            return output, CockpitState(previous_color="INVALID")

        epsilon = self.config.epsilon
        p1 = emission.p1
        projected_p1 = emission.projected_p1
        raw_direction = "UP" if p1 > epsilon else "DOWN" if p1 < -epsilon else "NEAR_ZERO"
        motion_state = self._motion_state(p1, emission.p2, projected_p1)

        velocity_scale = max(abs(p1), abs(projected_p1), epsilon)
        zero_proximity = abs(projected_p1) / velocity_scale
        opposing_change = 0.0
        if raw_direction == "UP":
            opposing_change = max(0.0, p1 - projected_p1)
        elif raw_direction == "DOWN":
            opposing_change = max(0.0, projected_p1 - p1)
        deceleration_strength = opposing_change / max(abs(p1), epsilon)

        opposing_direction = None
        if p1 > epsilon and emission.p2 < 0 and projected_p1 < p1:
            opposing_direction = "DOWN"
        elif p1 < -epsilon and emission.p2 > 0 and projected_p1 > p1:
            opposing_direction = "UP"
        opposing_count = (
            state.opposing_count + 1
            if opposing_direction is not None and opposing_direction == state.opposing_direction
            else 1 if opposing_direction is not None else 0
        )
        persistence_state = "NONE" if opposing_direction is None else f"{opposing_direction}_DECELERATION"

        crossing_direction = None
        if p1 > epsilon and projected_p1 <= 0:
            crossing_direction = "DOWN"
        elif p1 < -epsilon and projected_p1 >= 0:
            crossing_direction = "UP"
        near_zero = zero_proximity <= self.config.zero_proximity_threshold
        strong_deceleration = deceleration_strength >= self.config.deceleration_strength_threshold
        persistent = opposing_count >= self.config.persistence_observations

        candidate_direction = None
        reasons = [motion_state]
        if crossing_direction is not None:
            candidate_direction = crossing_direction
            reasons.append(f"PROJECTED_P1_{crossing_direction}_CROSS")
        elif opposing_direction is not None and persistent and near_zero and strong_deceleration:
            candidate_direction = opposing_direction
            reasons.extend(("PERSISTENT_DECELERATION", "PROJECTED_P1_ZERO_APPROACH"))

        candidate_age = 0
        if candidate_direction is not None:
            candidate_age = state.candidate_age + 1 if state.candidate_direction == candidate_direction else 1
        elif state.candidate_direction is not None and state.candidate_age < self.config.candidate_hold_observations:
            candidate_direction = state.candidate_direction
            candidate_age = state.candidate_age + 1
            reasons.append("CANDIDATE_HYSTERESIS")

        direct_direction_change = (
            candidate_direction is None
            and raw_direction in {"UP", "DOWN"}
            and (state.previous_color, raw_direction) in {("GREEN", "DOWN"), ("RED", "UP")}
        )
        if direct_direction_change:
            reasons.append("CURRENT_P1_DIRECTION_CROSS")

        confidence_caution = emission.confidence_state == "LOW" and self.config.low_confidence_requires_amber
        domain_caution = emission.domain_state == "OUT_OF_DOMAIN" and self.config.domain_exit_requires_amber
        if confidence_caution:
            reasons.append("LOW_CONFIDENCE")
        if domain_caution:
            reasons.append("DOMAIN_CAUTION")

        if raw_direction == "NEAR_ZERO":
            internal_state = "NEAR_STATIONARY"
            color = "AMBER"
            reasons.append("NEAR_STATIONARY")
        elif candidate_direction is not None:
            internal_state = f"TURN_{candidate_direction}_CANDIDATE"
            color = "AMBER"
        elif direct_direction_change:
            internal_state = "DIRECTION_CHANGE_TRANSITION"
            color = "AMBER"
        elif confidence_caution or domain_caution:
            internal_state = "UNCERTAIN"
            color = "AMBER"
        else:
            internal_state = motion_state
            color = "GREEN" if raw_direction == "UP" else "RED"

        output = PriceCockpitEmission(
            symbol=emission.symbol,
            timestamp=emission.timestamp,
            engine="P",
            raw_phase=emission.trajectory_phase,
            refined_internal_state=internal_state,
            p1_zero_proximity=zero_proximity,
            deceleration_strength=deceleration_strength,
            persistence_state=persistence_state,
            persistence_count=opposing_count,
            turn_candidate="NONE" if candidate_direction is None else candidate_direction,
            candidate_age=candidate_age,
            domain_state=emission.domain_state,
            confidence_state=emission.confidence_state,
            raw_direction=raw_direction,
            cockpit_color=color,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )
        next_state = CockpitState(
            previous_motion_state=motion_state,
            previous_color=color,
            opposing_direction=opposing_direction,
            opposing_count=opposing_count,
            candidate_direction=candidate_direction,
            candidate_age=candidate_age,
        )
        return output, next_state

    def _motion_state(self, p1: float, p2: float, projected_p1: float) -> str:
        epsilon = self.config.epsilon
        if abs(p1) <= epsilon:
            return "NEAR_STATIONARY"
        if p1 > epsilon:
            if p2 > 0 and projected_p1 >= p1:
                return "UP_ACCELERATING"
            if p2 < 0 and projected_p1 < p1:
                return "UP_DECELERATING"
            return "UP_STABLE"
        if p2 < 0 and projected_p1 <= p1:
            return "DOWN_ACCELERATING"
        if p2 > 0 and projected_p1 > p1:
            return "DOWN_DECELERATING"
        return "DOWN_STABLE"

    def _build_invalid(self, emission: PriceEmission) -> PriceCockpitEmission:
        reason = "RK_FAILURE" if not emission.rk_success else "NONFINITE_TRAJECTORY"
        return PriceCockpitEmission(
            symbol=emission.symbol,
            timestamp=emission.timestamp,
            engine="P",
            raw_phase=emission.trajectory_phase,
            refined_internal_state="INVALID",
            p1_zero_proximity=math.nan,
            deceleration_strength=math.nan,
            persistence_state="NONE",
            persistence_count=0,
            turn_candidate="NONE",
            candidate_age=0,
            domain_state=emission.domain_state,
            confidence_state=emission.confidence_state,
            raw_direction="INVALID",
            cockpit_color="INVALID",
            reason_codes=(reason,),
        )
