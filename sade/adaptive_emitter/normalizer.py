"""
Module/File Name: sade/adaptive_emitter/normalizer.py
Date Created / Migrated: August 25, 2026
Purpose:
    Provide the source-row to normalized observation mapping used by the
    migrated adaptive emitter seam.
Executive Overview:
    This module preserves the validated mapping semantics required by the
    adaptive emitter while removing runtime dependency on historical harness
    modules.
Role in SADE:
    Input normalization helper for adaptive emitter process calls.
Inputs:
    source_row dictionary and zero-based sequence index.
Outputs:
    sade.d01.v02.observations.NormalizedObservation or None.
Parameters / Configuration:
    entity_id set at normalizer construction.
Persistent State:
    entity_id.
External Dependencies:
    sade.d01.v02.observations.NormalizedObservation
Main Callers / Consumers:
    sade.adaptive_emitter.emitter.AdaptiveEmitter
Important Assumptions:
    source_row contains event_timestamp_utc, OHLCV, data_valid, session_type.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No synthetic timestamp generation
    - No cadence normalization
    - No session inference beyond pass-through placeholder use
Failure / Error Behavior:
    Returns None when required values cannot be parsed.
"""

from __future__ import annotations

from datetime import datetime as dt

from sade.d01.v02.observations import NormalizedObservation


class SourceRowNormalizer:
    """Map source-row records into D01 NormalizedObservation values."""

    def __init__(self, entity_id: str) -> None:
        self.entity_id = entity_id

    def source_row_to_normalized_observation(
        self,
        source_row: dict[str, str],
        row_index: int,
    ) -> NormalizedObservation | None:
        """Convert one source row into a normalized observation.

        Args:
            source_row: source dictionary containing timestamp and OHLCV fields.
            row_index: zero-based source sequence index.

        Returns:
            NormalizedObservation when parse succeeds, otherwise None.
        """
        try:
            event_timestamp_utc = source_row.get("event_timestamp_utc", "")
            parsed_utc = dt.fromisoformat(event_timestamp_utc.replace("Z", "+00:00"))
            event_time = parsed_utc.timestamp()
            receive_time = event_time

            close_price = float(source_row.get("close", 0.0))
            volume = float(source_row.get("volume", 0.0))

            data_valid = source_row.get("data_valid", "true").lower() == "true"
            quality_score = 1.0 if data_valid else 0.5
            session = source_row.get("session_type", "UNKNOWN")

            return NormalizedObservation(
                entity_id=self.entity_id,
                event_time=event_time,
                receive_time=receive_time,
                sequence_id=row_index,
                price=close_price,
                volume=volume,
                bid=None,
                ask=None,
                session=session,
                source_quality=quality_score,
                availability_mask={"price": True, "volume": True},
            )
        except Exception:
            return None
