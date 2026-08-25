"""
Module/File Name: sade/input/__init__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Export SADE input service client APIs.
Executive Overview:
    Provides a single import surface for SDX gRPC integration used by SADE.
Role in SADE:
    Input-service namespace boundary.
Inputs:
    Import requests.
Outputs:
    SDX client symbols.
Parameters / Configuration:
    None.
Persistent State:
    None.
External Dependencies:
    sade.input.sdx_client
Main Callers / Consumers:
    sade.adaptive_pipeline.pipeline
Important Assumptions:
    SDX transport remains gRPC V1.1.
Scientific Provenance:
    Input transport adapted from previously validated client behavior.
Explicit Exclusions / What This Module Does NOT Do:
    - No stream orchestration
    - No scientific processing
Failure / Error Behavior:
    Standard import errors only.
"""

from sade.input.sdx_client import DEFAULT_ENDPOINT, SadeSdxClient, StreamVectorRecord

__all__ = ["DEFAULT_ENDPOINT", "SadeSdxClient", "StreamVectorRecord"]
