"""
Module/File Name: sade/adaptive_emitter/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Export SADE adaptive emitter interfaces.
Executive Overview:
    Provides the migrated adaptive emitter implementation and normalization
    helper used by SADE adaptive pipeline.
Role in SADE:
    Scientific execution namespace for V0.1 adaptive path.
Inputs:
    Import requests from pipeline/runtime modules.
Outputs:
    AdaptiveEmitter and canonical hash utility.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    sade.adaptive_emitter.emitter
Main Callers / Consumers:
    sade.adaptive_pipeline.pipeline
Important Assumptions:
    Exported class signatures remain compatible with validated call path.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No stream orchestration
    - No network I/O
Failure / Error Behavior:
    Import errors propagate to callers.
"""

from sade.adaptive_emitter.emitter import AdaptiveEmitter, canonical_sha256

__all__ = ["AdaptiveEmitter", "canonical_sha256"]
