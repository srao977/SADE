"""
Module/File Name: sade/pricing_pipeline/price_engine/policy.py
Date Created / Migrated: August 25, 2026
Purpose:
    Implement migrated Price emission policy logic over derived trajectory inputs.
Executive Overview:
    Consumes p/p1/p2 and projected values, applies confidence and phase rules, and
    emits PriceEmission plus next PolicyState.
Role in SADE:
    Deterministic policy layer for price-emission interpretation.
Inputs:
    Numerical trajectory mapping and prior PolicyState.
Outputs:
    PriceEmission and next PolicyState.
Parameters / Configuration:
    PolicyConfig threshold and debounce parameters.
Persistent State:
    PolicyState is maintained externally by the caller.
External Dependencies:
    sade.pricing_pipeline.price_engine.contracts.PriceEmission and Python math/dataclasses.
Main Callers / Consumers:
    sade.pricing_pipeline.price_engine.engine and sade.pricing_pipeline.pipeline.
Important Assumptions:
    Inputs are causally ordered and represent upstream validated trajectory values.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF price_engine/policy.py
Explicit Exclusions / What This Module Does NOT Do:
    - Does not compute raw-price derivatives from close
    - Does not execute RK45
    - Does not execute F4 fitting
    - Does not produce BUY/HOLD/SELL trade actions
Failure / Error Behavior:
    Emits INVALID state for solver/non-finite conditions and raises KeyError/ValueError
    on missing or malformed required fields.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from .contracts import PriceEmission


@dataclass(frozen=True)
class PolicyConfig:
    """Immutable configuration for Price emission policy.

    Purpose:
        Hold confidence thresholds and reversal-debounce controls used by EmissionPolicy.
    Arguments / Inputs:
        policy_id, epsilon, and median/q95 thresholds for condition/eigenvalue/amplification.
    Returns / Outputs:
        Configuration dataclass used by policy runtime.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Thresholds are pre-validated by caller-controlled configuration.
    Failure / Error Behavior:
        No custom checks at construction; invalid values can degrade policy classification.
    Scientific Meaning:
        Encodes frozen policy calibration, not trajectory-generation mathematics.
    Original APTF Source:
        price_engine/policy.py::PolicyConfig
    Scientific Mathematics Changed:
        NO
    """

    policy_id: str
    epsilon: float
    condition_median: float
    condition_q95: float
    eigenvalue_median: float
    eigenvalue_q95: float
    amplification_median: float
    amplification_q95: float
    direct_reversal_debounce: bool


@dataclass(frozen=True)
class PolicyState:
    """Externally maintained policy transition state."""

    previous_color: str | None = None
    pending_reversal: str | None = None


def _direction(value: float, epsilon: float) -> str:
    if value > epsilon:
        return "UP"
    if value < -epsilon:
        return "DOWN"
    return "NEAR_ZERO"


def _acceleration(value: float) -> str:
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def _phase(p1: float, p2: float, projected_p1: float, epsilon: float) -> str:
    if abs(p1) <= epsilon:
        if projected_p1 > epsilon:
            return "TURNING_UP"
        if projected_p1 < -epsilon:
            return "TURNING_DOWN"
        return "NEAR_STATIONARY"
    if p1 > epsilon and projected_p1 <= -epsilon:
        return "TURNING_DOWN"
    if p1 < -epsilon and projected_p1 >= epsilon:
        return "TURNING_UP"
    if p1 > 0:
        return "UP_ACCELERATING" if p2 > 0 else "UP_DECELERATING"
    return "DOWN_DECELERATING" if p2 > 0 else "DOWN_ACCELERATING"


def _turning_tendency(p1: float, p2: float, projected_p1: float, projected_p2: float, epsilon: float) -> str:
    if p1 > epsilon and projected_p1 <= -epsilon:
        return "TURNING_DOWN"
    if p1 < -epsilon and projected_p1 >= epsilon:
        return "TURNING_UP"
    if p1 > epsilon and p2 < 0 and projected_p1 < p1:
        return "DETERIORATING_TOWARD_TURN"
    if p1 < -epsilon and p2 > 0 and projected_p1 > p1:
        return "RECOVERING_TOWARD_TURN"
    if p2 * projected_p2 < 0:
        return "PROJECTED_P2_REVERSAL"
    return "NONE"


class EmissionPolicy:
    """Deterministic policy that emits PriceEmission and next PolicyState."""

    def __init__(self, config: PolicyConfig):
        self.config = config

    def emit(self, numerical: Mapping[str, object], state: PolicyState) -> tuple[PriceEmission, PolicyState]:
        """Emit a PriceEmission and next state from trajectory inputs.

        Purpose:
            Apply phase, tendency, confidence, stability, and debounce rules.
        Arguments / Inputs:
            numerical trajectory mapping and prior PolicyState.
        Returns / Outputs:
            Tuple of PriceEmission and next PolicyState.
        Persistent State Changes:
            None internally; caller receives next state.
        Side Effects:
            None.
        Assumptions:
            Required numerical keys are present and represent the same timestamp.
        Failure / Error Behavior:
            Returns INVALID emission on solver/non-finite states; raises KeyError/ValueError
            if required keys are missing or malformed.
        Scientific Meaning:
            Policy interpretation over provided trajectory state; does not run RK45/F4.
        Original APTF Source:
            price_engine/policy.py::EmissionPolicy.emit
        Scientific Mathematics Changed:
            NO
        """

        required = ("p", "p1", "p2", "projected_p", "projected_p1", "projected_p2")
        finite = all(math.isfinite(float(numerical[name])) for name in required)
        rk_success = bool(numerical["rk_success"])
        reasons: list[str] = []
        if not rk_success or not finite:
            reasons.append("RK_FAILURE" if not rk_success else "NONFINITE_TRAJECTORY")
            emission = self._build(numerical, "UNCERTAIN", "NONE", "INVALID", "INVALID", "INVALID", reasons)
            return emission, PolicyState(previous_color="INVALID", pending_reversal=None)

        p1 = float(numerical["p1"])
        p2 = float(numerical["p2"])
        projected_p1 = float(numerical["projected_p1"])
        projected_p2 = float(numerical["projected_p2"])
        phase = _phase(p1, p2, projected_p1, self.config.epsilon)
        tendency = _turning_tendency(p1, p2, projected_p1, projected_p2, self.config.epsilon)
        reasons.append(phase)
        if tendency != "NONE":
            reasons.append(tendency)

        domain = "OUT_OF_DOMAIN" if bool(numerical["domain_exit"]) else "IN_DOMAIN"
        condition = float(numerical["condition_number"])
        eigenvalue = float(numerical["max_real_eigenvalue"])
        amplification = float(numerical["perturbation_amplification"])
        if domain == "OUT_OF_DOMAIN":
            confidence = "LOW"
            reasons.extend(("DOMAIN_EXIT", "LOW_CONFIDENCE"))
        elif condition <= self.config.condition_median and eigenvalue <= self.config.eigenvalue_median and amplification <= self.config.amplification_median:
            confidence = "HIGH"
        elif condition <= self.config.condition_q95 and eigenvalue <= self.config.eigenvalue_q95 and amplification <= self.config.amplification_q95:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
            reasons.append("LOW_CONFIDENCE")

        stability = "STABLE" if eigenvalue <= 0 else "LOCALLY_EXPANSIVE"
        if stability == "LOCALLY_EXPANSIVE":
            reasons.append("POSITIVE_MAX_REAL_EIGENVALUE")

        if confidence == "LOW" or phase in {"UP_DECELERATING", "DOWN_DECELERATING", "NEAR_STATIONARY", "UNCERTAIN"}:
            raw_color = "AMBER"
        elif phase in {"UP_ACCELERATING", "TURNING_UP"} and projected_p1 > self.config.epsilon:
            raw_color = "GREEN"
        elif phase in {"DOWN_ACCELERATING", "TURNING_DOWN"} and projected_p1 < -self.config.epsilon:
            raw_color = "RED"
        else:
            raw_color = "AMBER"

        color = raw_color
        pending = None
        direct_reversal = (state.previous_color, raw_color) in {("GREEN", "RED"), ("RED", "GREEN")}
        if self.config.direct_reversal_debounce and direct_reversal and state.pending_reversal != raw_color:
            color = "AMBER"
            pending = raw_color
            reasons.append("DIRECT_REVERSAL_DEBOUNCE")
        elif self.config.direct_reversal_debounce and state.pending_reversal == raw_color:
            pending = None

        emission = self._build(numerical, phase, tendency, domain, stability, confidence, reasons, raw_color, color)
        return emission, PolicyState(previous_color=color, pending_reversal=pending)

    def _build(
        self,
        numerical: Mapping[str, object],
        phase: str,
        tendency: str,
        domain: str,
        stability: str,
        confidence: str,
        reasons: list[str],
        raw_color: str = "INVALID",
        color: str = "INVALID",
    ) -> PriceEmission:
        """Build immutable PriceEmission from validated policy intermediates.

        Original APTF Source:
            price_engine/policy.py::EmissionPolicy._build
        Scientific Mathematics Changed:
            NO
        """

        p = float(numerical["p"])
        p1 = float(numerical["p1"])
        p2 = float(numerical["p2"])
        projected_p = float(numerical["projected_p"])
        projected_p1 = float(numerical["projected_p1"])
        projected_p2 = float(numerical["projected_p2"])
        return PriceEmission(
            symbol=str(numerical["symbol"]),
            timestamp=str(numerical["timestamp"]),
            engine="P",
            p=p,
            p1=p1,
            p2=p2,
            projected_p=projected_p,
            projected_p1=projected_p1,
            projected_p2=projected_p2,
            delta_projected_p=projected_p - p,
            delta_projected_p1=projected_p1 - p1,
            delta_projected_p2=projected_p2 - p2,
            current_direction=_direction(p1, self.config.epsilon),
            current_acceleration=_acceleration(p2),
            projected_direction=_direction(projected_p1, self.config.epsilon),
            projected_acceleration=_acceleration(projected_p2),
            trajectory_phase=phase,
            turning_tendency=tendency,
            domain_state=domain,
            stability_state=stability,
            confidence_state=confidence,
            raw_color=raw_color,
            color=color,
            reason_codes=tuple(dict.fromkeys(reasons)),
            rk_success=bool(numerical["rk_success"]),
            condition_number=float(numerical["condition_number"]),
            max_real_eigenvalue=float(numerical["max_real_eigenvalue"]),
            perturbation_amplification=float(numerical["perturbation_amplification"]),
        )
