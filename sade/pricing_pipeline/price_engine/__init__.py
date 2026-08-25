"""
Module/File Name: sade/pricing_pipeline/price_engine/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Export SADE-owned migrated Price Engine public API.
Executive Overview:
    Re-exports immutable contracts, policy objects, cockpit objects, and runtime
    engine entrypoint required by SADE pricing pipeline.
Role in SADE:
    Internal package surface for pricing_pipeline.
Inputs:
    Python imports from pricing_pipeline modules and tests.
Outputs:
    Stable exported symbols for Price engine usage.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    sade.pricing_pipeline.price_engine contracts/policy/engine/cockpit.
Main Callers / Consumers:
    sade.pricing_pipeline.pipeline and test suite.
Important Assumptions:
    Exported names remain stable for SADE pricing integration.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF price_engine package (contracts, engine, policy, cockpit)
Explicit Exclusions / What This Module Does NOT Do:
    - No numerical computation
    - No trajectory solving
    - No execution BUY/HOLD/SELL synthesis
Failure / Error Behavior:
    Standard import errors propagate to caller.
"""

from .cockpit import CockpitPolicyConfig, CockpitState, PriceCockpitEmission, PriceCockpitInterpreter
from .contracts import MarketObservation, PriceEmission
from .engine import PriceEngine
from .policy import EmissionPolicy, PolicyConfig, PolicyState

__all__ = [
    "CockpitPolicyConfig",
    "CockpitState",
    "EmissionPolicy",
    "MarketObservation",
    "PolicyConfig",
    "PolicyState",
    "PriceCockpitEmission",
    "PriceCockpitInterpreter",
    "PriceEmission",
    "PriceEngine",
]
