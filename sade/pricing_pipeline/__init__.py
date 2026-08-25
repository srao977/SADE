"""
Module/File Name: sade/pricing_pipeline/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Export SADE pricing pipeline public API.
Executive Overview:
    Provides the PricingPipeline entrypoint and configuration types.
Role in SADE:
    SADE-owned Price-side package boundary.
Inputs:
    Import requests.
Outputs:
    Pricing pipeline API symbols.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    sade.pricing_pipeline.pipeline.
Main Callers / Consumers:
    SADE unit run wiring and integration tests.
Important Assumptions:
    Package is consumed as downstream of SADE adaptive pipeline output.
Scientific Provenance:
    Consolidates migrated mathematics from APTF Test009/Test013B/Test014 and
    migrated generic APTF price_engine package.
Explicit Exclusions / What This Module Does NOT Do:
    - No SDX transport
    - No volume pipeline
    - No final execution BUY/HOLD/SELL synthesis
Failure / Error Behavior:
    Import errors propagate to caller.
"""

from .pipeline import PricingPipeline, PricingPipelineConfig

__all__ = ["PricingPipeline", "PricingPipelineConfig"]
