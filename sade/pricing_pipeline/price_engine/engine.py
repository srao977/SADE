"""
Module/File Name: sade/pricing_pipeline/price_engine/engine.py
Date Created / Migrated: August 25, 2026
Purpose:
    Provide the migrated PriceEngine runtime entrypoint over validated policy logic.
Executive Overview:
    Validates entity/timestamp coherence between observation and numerical payload,
    then delegates to EmissionPolicy.
Role in SADE:
    Price-emission runtime orchestrator with no trajectory-generation authority.
Inputs:
    MarketObservation, numerical trajectory mapping, and external PolicyState.
Outputs:
    PriceEmission and next PolicyState.
Parameters / Configuration:
    EmissionPolicy instance.
Persistent State:
    None in engine; state is caller-owned PolicyState.
External Dependencies:
    sade.pricing_pipeline.price_engine.contracts and policy.
Main Callers / Consumers:
    sade.pricing_pipeline.pipeline.
Important Assumptions:
    Numerical payload and observation represent the same causal timestamp and entity.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF price_engine/engine.py
Explicit Exclusions / What This Module Does NOT Do:
    - Does not compute raw-price derivatives from close
    - Does not execute RK45
    - Does not execute F4
    - Does not generate BUY/HOLD/SELL directly
Failure / Error Behavior:
    Raises ValueError on entity/timestamp mismatch; propagates policy exceptions.
"""

from __future__ import annotations

from typing import Mapping

from .contracts import MarketObservation, PriceEmission
from .policy import EmissionPolicy, PolicyState


class PriceEngine:
    """Price engine wrapper around EmissionPolicy.

    Purpose:
        Enforce input coherence checks and return deterministic policy emissions.
    Arguments / Inputs:
        policy.
    Returns / Outputs:
        PriceEngine instance.
    Persistent State Changes:
        Stores policy reference only.
    Side Effects:
        None.
    Assumptions:
        Policy configuration is frozen/validated by caller.
    Failure / Error Behavior:
        Constructor has no explicit validation.
    Scientific Meaning:
        Orchestration seam only; does not alter policy mathematics.
    Original APTF Source:
        price_engine/engine.py::PriceEngine
    Scientific Mathematics Changed:
        NO
    """

    def __init__(self, policy: EmissionPolicy):
        self.policy = policy

    def observe(
        self,
        observation: MarketObservation,
        numerical_trajectory: Mapping[str, object],
        policy_state: PolicyState,
    ) -> tuple[PriceEmission, PolicyState]:
        """Run one Price observation step.

        Purpose:
            Validate entity/timestamp coherence and emit PriceEmission via policy.
        Arguments / Inputs:
            observation, numerical_trajectory, policy_state.
        Returns / Outputs:
            Tuple of PriceEmission and next PolicyState.
        Persistent State Changes:
            None internally; caller receives next PolicyState.
        Side Effects:
            None.
        Assumptions:
            numerical_trajectory contains symbol and timestamp matching observation.
        Failure / Error Behavior:
            Raises ValueError for entity/timestamp mismatch.
        Scientific Meaning:
            Generalized instrument gate only; no mathematics change.
        Original APTF Source:
            price_engine/engine.py::PriceEngine.observe
        Scientific Mathematics Changed:
            NO
        """

        expected_symbol = str(numerical_trajectory["symbol"])
        if observation.symbol != expected_symbol:
            raise ValueError(
                "observation symbol and trajectory symbol differ "
                f"observation={observation.symbol} trajectory={expected_symbol}"
            )
        if str(numerical_trajectory["timestamp"]) != observation.timestamp:
            raise ValueError("observation and trajectory timestamps differ")
        return self.policy.emit(numerical_trajectory, policy_state)
