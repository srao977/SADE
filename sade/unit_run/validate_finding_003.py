"""
Module/File Name: sade/unit_run/validate_finding_003.py
Date Created / Modified: August 27, 2026
Purpose:
    Validate bounded production collection behavior for Python-Prove Finding 003.
Executive Overview:
    Replays accepted source values through production-default Adaptive and Pricing
    objects, records collection checkpoints, and performs a longer neutral replay.
Role in SADE:
    Validation-only evidence generator for the bounded-state correction.
Inputs:
    Finding 003 before Adaptive observations CSV.
Outputs:
    collection_after.json and long_run/long_run_boundedness.json.
Parameters / Configuration:
    Input CSV, output root, and long-run observation count.
Persistent State:
    Validation-local pipeline instances only.
External Dependencies:
    Python standard library and current SADE production pipelines.
Main Callers / Consumers:
    Manual Finding 003 validation and run documentation.
Important Assumptions:
    The input CSV is the accepted ordered unchanged-SDX 100-observation artifact.
Scientific Provenance:
    Uses current production science unchanged; longer replay is memory evidence only.
Explicit Exclusions / What This Module Does NOT Do:
    No SDX, equation, ID, ingress, projection, or production configuration changes.
Failure / Error Behavior:
    Raises on malformed input, processing failure, or any exceeded production bound.
Previous Retention:
    Not applicable; validation-only module.
New Retention:
    Stores checkpoint summaries only, never full long-run output history.
Scientific State Removed:
    NO
Scientific Mathematics Changed:
    NO
Hot-Memory Behavior Changed:
    NO; this module observes production behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sade.adaptive_pipeline.pipeline import AdaptivePipeline, AdaptivePipelineConfig
from sade.pricing_pipeline.pipeline import PricingPipeline, PricingPipelineConfig


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _vector(row: dict[str, str], index: int, timestamp: str) -> SimpleNamespace:
    return SimpleNamespace(
        entity_id=row["entity_id"],
        source_row_index=index,
        source_timestamp=timestamp,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=int(row["volume"]),
    )


def _collection_state(adaptive: AdaptivePipeline, pricing: PricingPipeline) -> dict[str, int]:
    """Return retained production sizes without capturing output history.

    Purpose:
        Measure every persistent Finding 003 collection group at one checkpoint.
    Arguments / Inputs:
        Live production-default Adaptive and Pricing pipeline instances.
    Returns / Outputs:
        Mapping from collection group to current retained size.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Diagnostic and record retention use their production defaults.
    Failure / Error Behavior:
        Attribute errors expose a changed retention contract.
    Scientific Meaning:
        None; collection-length observation only.
    Retention Semantics:
        Reads lengths/counters without adding retained references.
    """

    emitter = adaptive._emitter
    return {
        "AdaptiveEmitter.emissions": len(emitter.emissions),
        "AdaptiveEmitter.initialization": len(emitter.initialization),
        "AdaptiveEmitter.adaptation_audit": len(emitter.adaptation_audit),
        "AdaptiveEmitter.feedback_audit": len(emitter.feedback_audit),
        "D01V02Model.trace_records": len(emitter.d01.trace_records),
        "AdaptivePipeline._rows": len(adaptive._rows),
        "PricingPipeline.price_time_ohlcv_history": len(pricing._closes),
        "PricingPipeline.derivative_history": len(pricing._p1),
        "PricingPipeline._source_row_index": int(pricing._last_source_row_index is not None),
        "AdaptivePipeline.run_metric_aggregate_slots": 13,
    }


def _event_counts(adaptive: AdaptivePipeline) -> dict[str, int]:
    emitter = adaptive._emitter
    return {
        "emission_count": emitter.emission_count,
        "initialization_count": emitter.initialization_count,
        "adaptation_event_count": emitter.adaptation_event_count,
        "feedback_event_count": emitter.feedback_event_count,
        "trace_count": emitter.d01.trace_count,
    }


def _run_replay(
    rows: list[dict[str, str]],
    count: int,
    checkpoints: set[int],
    *,
    preserve_source_timestamps: bool,
) -> dict[str, Any]:
    """Run deterministic memory validation with monotonic replay lineage.

    Purpose:
        Prove retained collection sizes stop growing while processing continues.
    Arguments / Inputs:
        Accepted source rows, replay count, and requested checkpoints.
    Returns / Outputs:
        Checkpoint collection sizes, event counters, and final summaries.
    Persistent State Changes:
        Advances validation-local production pipeline instances.
    Side Effects:
        None; no full output collector is enabled.
    Assumptions:
        Repeated OHLCV values are neutral memory-test stimuli, not scientific evidence.
    Failure / Error Behavior:
        Processing and bound assertion failures propagate.
    Scientific Meaning:
        The first 100 exact rows support equivalence; repetitions prove memory only.
    Retention Semantics:
        Production diagnostic/output histories remain zero and Pricing remains at its
        configuration-derived 31-row bound throughout the replay.
    """

    adaptive = AdaptivePipeline(
        AdaptivePipelineConfig(entity="AAPL", max_vectors=count),
        client=object(),
    )
    pricing = PricingPipeline(PricingPipelineConfig(entity="AAPL"))
    start = datetime(2026, 8, 27, 13, 30, tzinfo=timezone.utc)
    evidence: dict[str, Any] = {
        "0": {"collections": _collection_state(adaptive, pricing), "events": _event_counts(adaptive)}
    }
    emissions_after_100 = 0
    for index in range(count):
        row = rows[index % len(rows)]
        timestamp = (
            row["source_timestamp"]
            if preserve_source_timestamps
            else (start + timedelta(minutes=index)).isoformat().replace("+00:00", "Z")
        )
        adaptive_record = adaptive.process_vector(_vector(row, index, timestamp))
        pricing_step = pricing.process(adaptive_record)
        if index >= 100 and pricing_step["price_emission"] is not None:
            emissions_after_100 += 1
        processed = index + 1
        if processed in checkpoints:
            evidence[str(processed)] = {
                "collections": _collection_state(adaptive, pricing),
                "events": _event_counts(adaptive),
            }

    final_collections = _collection_state(adaptive, pricing)
    assert all(
        final_collections[name] == 0
        for name in (
            "AdaptiveEmitter.emissions",
            "AdaptiveEmitter.initialization",
            "AdaptiveEmitter.adaptation_audit",
            "AdaptiveEmitter.feedback_audit",
            "D01V02Model.trace_records",
            "AdaptivePipeline._rows",
        )
    )
    assert final_collections["PricingPipeline.price_time_ohlcv_history"] <= pricing._history_limit
    assert final_collections["PricingPipeline.derivative_history"] <= pricing._history_limit
    assert final_collections["PricingPipeline._source_row_index"] <= 1
    return {
        "checkpoints": evidence,
        "configured_scientific_bound": pricing._history_limit,
        "emissions_after_observation_100": emissions_after_100,
        "final_collections": final_collections,
        "observations_processed": count,
        "pricing_summary": pricing.summary(),
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Python-Prove Finding 003")
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("output/python_prove/finding_003/before/adaptive/observations.csv"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("output/python_prove/finding_003"),
    )
    parser.add_argument("--long-run-observations", type=int, default=1000)
    args = parser.parse_args()
    rows = _load_rows(args.input_csv)
    if len(rows) != 100:
        raise ValueError(f"EXPECTED_100_ACCEPTED_ROWS got={len(rows)}")

    after = _run_replay(
        rows,
        100,
        {25, 50, 75, 100},
        preserve_source_timestamps=True,
    )
    long_run = _run_replay(
        rows,
        args.long_run_observations,
        {15, 100, 250, 500, args.long_run_observations},
        preserve_source_timestamps=False,
    )
    _write_json(args.output_root / "collection_after.json", after)
    _write_json(args.output_root / "long_run" / "long_run_boundedness.json", long_run)
    print(json.dumps({"after": after, "long_run": long_run}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())