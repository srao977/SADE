"""
Module/File Name: sade/adaptive_pipeline/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Export SADE adaptive pipeline public API.
Executive Overview:
    Provides stable import symbols for SADE V0.1 orchestration layer.
Role in SADE:
    Product-level entrypoint for adaptive pipeline runtime use.
Inputs:
    Import requests.
Outputs:
    AdaptivePipeline API symbols.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    sade.adaptive_pipeline.pipeline
Main Callers / Consumers:
    sade CLI and programmatic users.
Important Assumptions:
    API reflects SADE-owned independent runtime boundaries.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No runtime stream processing
    - No scientific computation
Failure / Error Behavior:
    Import errors propagate to caller.
"""

from sade.adaptive_pipeline.pipeline import (
    DEFAULT_UNIT_RUN_OUTPUT_DIR,
    AdaptivePipeline,
    AdaptivePipelineConfig,
    build_source_row,
    physical_row_from_source_index,
)

__all__ = [
    "DEFAULT_UNIT_RUN_OUTPUT_DIR",
    "AdaptivePipeline",
    "AdaptivePipelineConfig",
    "build_source_row",
    "physical_row_from_source_index",
]
