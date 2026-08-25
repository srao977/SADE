"""
Module/File Name: sade/configuration/scientific_baseline.py
Date Created / Migrated: August 25, 2026
Purpose:
    Store SADE-owned immutable scientific provenance identifiers required by
    the migrated adaptive emitter interface.
Executive Overview:
    The frozen adaptive emitter accepts rule and implementation fingerprints.
    In SADE, these values are owned locally rather than read from external
    repository artifacts.
Role in SADE:
    Internal baseline identity provider for pipeline/emitter wiring.
Inputs:
    None at runtime.
Outputs:
    Rule and implementation fingerprint constants.
Parameters / Configuration:
    BASELINE_RULE_FINGERPRINT, BASELINE_IMPLEMENTATION_FINGERPRINT.
Persistent State:
    None.
External Dependencies:
    None.
Main Callers / Consumers:
    sade.adaptive_pipeline.pipeline
Important Assumptions:
    Fingerprints are provenance identities and do not alter mathematics.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No external file reads
    - No cryptographic recomputation
    - No scientific parameter tuning
Failure / Error Behavior:
    Missing/blank constants should be treated as configuration failure by
    callers.
"""

BASELINE_RULE_FINGERPRINT = "c4c5bbf36ab97b3e7fc4628dfe11708947f996bcd79901a9d19b6a0f2049e9e2"
BASELINE_IMPLEMENTATION_FINGERPRINT = "e8b736dfba03b454633831585222d5270c18b7f8eae510b34ee19dc1f5c58410"


def get_baseline_fingerprints() -> tuple[str, str]:
    """Return SADE-owned scientific baseline fingerprints.

    Returns:
        A tuple of (rule_fingerprint, implementation_fingerprint).

    Raises:
        RuntimeError: If either fingerprint is empty.
    """
    if not BASELINE_RULE_FINGERPRINT or not BASELINE_IMPLEMENTATION_FINGERPRINT:
        raise RuntimeError("MISSING_SADE_BASELINE_METADATA")
    return BASELINE_RULE_FINGERPRINT, BASELINE_IMPLEMENTATION_FINGERPRINT
