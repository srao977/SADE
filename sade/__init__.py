"""
Module/File Name: sade/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Define SADE package identity and exported version.
Executive Overview:
    SADE (Self Adaptive Decision Engine) V0.1 exposes the adaptive pipeline as
    the first independent runtime capability.
Role in SADE:
    Root namespace and product metadata anchor.
Inputs:
    Import requests from callers.
Outputs:
    Package version metadata.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    None.
Main Callers / Consumers:
    CLI entrypoint, tests, downstream application imports.
Important Assumptions:
    Version identifier is stable for V0.1 release outputs.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No runtime orchestration
    - No scientific computation
Failure / Error Behavior:
    None beyond normal Python import behavior.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
