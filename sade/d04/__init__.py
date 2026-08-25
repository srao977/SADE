"""
Module/File Name: sade/d04/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    SADE D04 namespace for migrated capturability components required by V0.1.
Executive Overview:
    Exposes only the D04 modules required by adaptive pipeline execution.
Role in SADE:
    Scientific dependency namespace.
Inputs:
    Import requests.
Outputs:
    D04 capturability exports.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    sade.d04.envelope, sade.d04.models
Main Callers / Consumers:
    sade.adaptive_emitter.emitter
Important Assumptions:
    Stateful trading envelope runtime is intentionally excluded in V0.1.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No old stateful TradingEnvelope runtime
    - No D03 orchestration
Failure / Error Behavior:
    Standard import failure behavior.
"""

from sade.d04.envelope import CapturabilityModelV0_2
from sade.d04.models import CapturabilityResult, EnvelopeContext

__all__ = ["CapturabilityModelV0_2", "CapturabilityResult", "EnvelopeContext"]
