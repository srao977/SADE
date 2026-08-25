"""
Module/File Name: sade/pricing_pipeline/price_engine/contracts.py
Date Created / Migrated: August 25, 2026
Purpose:
    Define immutable input/output contracts for the migrated Price Engine.
Executive Overview:
    Provides typed dataclasses for market observation input and PriceEmission output.
Role in SADE:
    Contract boundary between pricing mathematics and PriceEngine policy emission.
Inputs:
    Market observation metadata and numerical state values.
Outputs:
    Immutable PriceEmission payloads with trajectory diagnostics.
Parameters / Configuration:
    Dataclass fields only.
Persistent State:
    None.
External Dependencies:
    Python dataclasses and typing.
Main Callers / Consumers:
    sade.pricing_pipeline.price_engine.engine, policy, cockpit, and pipeline.
Important Assumptions:
    Numerical values are produced by the pricing pipeline mathematics.
Scientific Provenance:
    Migrated without mathematical change from:
    - APTF price_engine/contracts.py
Explicit Exclusions / What This Module Does NOT Do:
    - No derivative computation
    - No RK45 solving
    - No final execution decision synthesis
Failure / Error Behavior:
    No explicit runtime validation in dataclasses; field-type misuse surfaces in callers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MarketObservation:
    """Immutable market observation envelope consumed by PriceEngine.

    Purpose:
        Hold observation-level metadata and OHLCV values passed into engine validation.
    Arguments / Inputs:
        symbol, timestamp, open, high, low, close, volume, session, source.
    Returns / Outputs:
        Dataclass instance for immutable pass-through usage.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Caller provides causally ordered observations.
    Failure / Error Behavior:
        No custom checks; errors occur only if caller provides incompatible values.
    Scientific Meaning:
        Metadata carrier only; does not alter trajectory mathematics.
    Original APTF Source:
        price_engine/contracts.py::MarketObservation
    Scientific Mathematics Changed:
        NO
    """

    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    session: str
    source: str

    def as_dict(self) -> dict[str, Any]:
        """Return dict serialization of the observation.

        Purpose:
            Provide portable serialization for diagnostics and downstream adapters.
        Arguments / Inputs:
            None.
        Returns / Outputs:
            Dictionary representation of all dataclass fields.
        Persistent State Changes:
            None.
        Side Effects:
            None.
        Assumptions:
            Dataclass fields are serializable.
        Failure / Error Behavior:
            Standard dataclass conversion errors if fields contain unsupported objects.
        Scientific Meaning:
            Serialization only; no mathematical transformation.
        Original APTF Source:
            price_engine/contracts.py::MarketObservation.as_dict
        Scientific Mathematics Changed:
            NO
        """

        return asdict(self)


@dataclass(frozen=True)
class PriceEmission:
    """Immutable Price Engine emission payload.

    Purpose:
        Capture trajectory phase/turning interpretation and confidence diagnostics.
    Arguments / Inputs:
        Derived p/p1/p2 and projected values, domain/stability states, and metadata.
    Returns / Outputs:
        Dataclass instance carrying complete PriceEmission contract.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Values originate from validated pricing trajectory producers.
    Failure / Error Behavior:
        No custom checks; invalid field types are caller errors.
    Scientific Meaning:
        Represents policy interpretation output, not trade-action authority.
    Original APTF Source:
        price_engine/contracts.py::PriceEmission
    Scientific Mathematics Changed:
        NO
    """

    symbol: str
    timestamp: str
    engine: str
    p: float
    p1: float
    p2: float
    projected_p: float
    projected_p1: float
    projected_p2: float
    delta_projected_p: float
    delta_projected_p1: float
    delta_projected_p2: float
    current_direction: str
    current_acceleration: str
    projected_direction: str
    projected_acceleration: str
    trajectory_phase: str
    turning_tendency: str
    domain_state: str
    stability_state: str
    confidence_state: str
    raw_color: str
    color: str
    reason_codes: tuple[str, ...]
    rk_success: bool
    condition_number: float
    max_real_eigenvalue: float
    perturbation_amplification: float

    def as_dict(self) -> dict[str, Any]:
        """Return dict serialization with JSON-friendly reason codes.

        Purpose:
            Serialize immutable emission for CSV/JSON persistence.
        Arguments / Inputs:
            None.
        Returns / Outputs:
            Dictionary where reason_codes is converted from tuple to list.
        Persistent State Changes:
            None.
        Side Effects:
            None.
        Assumptions:
            Field values are serializable primitives.
        Failure / Error Behavior:
            Standard conversion failures for non-serializable values.
        Scientific Meaning:
            Serialization adapter only; no policy or numerical changes.
        Original APTF Source:
            price_engine/contracts.py::PriceEmission.as_dict
        Scientific Mathematics Changed:
            NO
        """

        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload
