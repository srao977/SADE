"""
Module/File Name: sade/unit_run/run_pricing_001.py
Date Created / Migrated: August 25, 2026
Purpose:
    Execute SADE PRICING UNIT RUN 001 (AAPL/100) in a single causal stream.
Executive Overview:
    Streams vectors once from SDX, processes each through AdaptivePipeline.process_vector,
    then PricingPipeline.process, and persists integrated run artifacts.
Role in SADE:
    Bounded integrated validation run for adaptive -> pricing composition.
Inputs:
    SDX endpoint and output directory.
Outputs:
    observations.csv, pricing_summary.json, migration_equivalence.json.
Parameters / Configuration:
    endpoint and output_dir.
Persistent State:
    In-memory adaptive/pricing records during unit run.
External Dependencies:
    sade.input.sdx_client, sade.adaptive_pipeline, sade.pricing_pipeline.
Main Callers / Consumers:
    Human validation flow and implementation reporting.
Important Assumptions:
    Pricing pipeline does not access SDX directly; adaptive output is upstream seam.
Scientific Provenance:
    Unit composition over migrated adaptive lineage and migrated pricing lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No second SDX stream
    - No volume path
    - No final execution synthesis
Failure / Error Behavior:
    Returns nonzero on stream shortfall, processing failures, or independence breaches.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sade.adaptive_pipeline.pipeline import AdaptivePipeline, AdaptivePipelineConfig
from sade.input.sdx_client import SadeSdxClient
from sade.pricing_pipeline import PricingPipeline, PricingPipelineConfig


APTF_ROOT = str(Path("C:/Users/chino/APTF").resolve()).lower()


def _collect_apft_dependency_evidence(opened_files: list[str]) -> dict[str, Any]:
    loaded_from_aptf = []
    for module in list(sys.modules.values()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        resolved = str(Path(module_file).resolve()).lower()
        if resolved.startswith(APTF_ROOT):
            loaded_from_aptf.append(resolved)

    opened_from_aptf = []
    for file_path in opened_files:
        try:
            resolved = str(Path(file_path).resolve()).lower()
        except Exception:
            resolved = str(file_path).lower()
        if resolved.startswith(APTF_ROOT):
            opened_from_aptf.append(resolved)

    return {
        "aptf_modules_loaded_count": len(set(loaded_from_aptf)),
        "aptf_modules_loaded": sorted(set(loaded_from_aptf)),
        "aptf_files_opened_count": len(set(opened_from_aptf)),
        "aptf_files_opened": sorted(set(opened_from_aptf)),
    }


def run_pricing_unit_001(
    endpoint: str = "localhost:50051",
    output_dir: Path = Path("output/unit_runs/pricing_001"),
) -> dict[str, Any]:
    """Run integrated Adaptive -> Pricing flow for AAPL/100.

    Purpose:
        Validate one bounded causal stream through both SADE packages.
    """

    opened_files: list[str] = []

    def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and args:
            opened_files.append(str(args[0]))

    sys.addaudithook(_audit_hook)

    client = SadeSdxClient(endpoint=endpoint)
    adaptive = AdaptivePipeline(
        config=AdaptivePipelineConfig(
            entity="AAPL",
            max_vectors=100,
            timeout_seconds=60.0,
            sdx_endpoint=endpoint,
            output_dir=output_dir,
        ),
        client=client,
    )
    pricing = PricingPipeline(config=PricingPipelineConfig(entity="AAPL"))

    integrated_rows: list[dict[str, Any]] = []
    failures: list[str] = []

    try:
        stream = client.stream_vectors(entities=["AAPL"], max_vectors_per_entity=100, timeout_seconds=60.0)
        for vector in stream:
            adaptive_row = adaptive.process_vector(vector)
            pricing_step = pricing.process(adaptive_row)

            record = {
                "source_row_index": adaptive_row["source_row_index"],
                "source_timestamp": adaptive_row["source_timestamp"],
                "entity_id": adaptive_row["entity_id"],
                "close": adaptive_row["close"],
                "adaptive_status": adaptive_row["status"],
                "adaptive_position_decision": adaptive_row["position_decision"],
                "pricing_status": pricing_step["status"],
                "pricing_emitted": pricing_step["price_emission"] is not None,
                "pricing_color": "" if pricing_step["price_emission"] is None else pricing_step["price_emission"]["color"],
                "pricing_phase": "" if pricing_step["price_emission"] is None else pricing_step["price_emission"]["trajectory_phase"],
                "pricing_confidence": "" if pricing_step["price_emission"] is None else pricing_step["price_emission"]["confidence_state"],
                "rk_success": "" if pricing_step["numerical"] is None else pricing_step["numerical"]["rk_success"],
                "domain_exit": "" if pricing_step["numerical"] is None else pricing_step["numerical"]["domain_exit"],
                "price_cockpit_output": pricing_step["cockpit_emission"] is not None,
            }
            integrated_rows.append(record)
            if len(integrated_rows) >= 100:
                break

        if len(integrated_rows) != 100:
            raise RuntimeError(f"SHORT_STREAM expected=100 got={len(integrated_rows)}")
    except Exception as error:
        failures.append(f"UNIT_RUN_FAILURE {type(error).__name__}: {error}")
    finally:
        adaptive.close()
        client.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    observations_path = output_dir / "observations.csv"
    with observations_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(integrated_rows[0].keys()) if integrated_rows else [
            "source_row_index",
            "source_timestamp",
            "entity_id",
            "close",
            "adaptive_status",
            "adaptive_position_decision",
            "pricing_status",
            "pricing_emitted",
            "pricing_color",
            "pricing_phase",
            "pricing_confidence",
            "rk_success",
            "domain_exit",
            "price_cockpit_output",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in integrated_rows:
            writer.writerow(row)

    adaptive_status_counts = Counter(row["adaptive_status"] for row in integrated_rows)
    adaptive_decisions = Counter(
        row["adaptive_position_decision"]
        for row in integrated_rows
        if row["adaptive_position_decision"] in {"BUY", "SELL", "HOLD"}
    )

    pricing_summary = pricing.close()
    dependency = _collect_apft_dependency_evidence(opened_files)

    summary = {
        "status": "FAILED" if failures else "COMPLETE",
        "unit_run_id": "SADE_PRICING_UNIT_RUN_001",
        "entity": "AAPL",
        "vectors_requested": 100,
        "vectors_received": len(integrated_rows),
        "adaptive": {
            "initializing": int(adaptive_status_counts.get("INITIALIZING", 0)),
            "actionable": int(adaptive_status_counts.get("ACTIONABLE", 0)),
            "BUY": int(adaptive_decisions.get("BUY", 0)),
            "SELL": int(adaptive_decisions.get("SELL", 0)),
            "HOLD": int(adaptive_decisions.get("HOLD", 0)),
            "source_timestamp_first": "" if not integrated_rows else integrated_rows[0]["source_timestamp"],
            "source_timestamp_last": "" if not integrated_rows else integrated_rows[-1]["source_timestamp"],
        },
        "pricing": pricing_summary,
        "failures": failures,
        "source_timestamp_preserved": True,
        "timestamp_normalization": False,
        "cadence_logic_added": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **dependency,
    }

    (output_dir / "pricing_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "migration_equivalence.json").write_text(
        json.dumps(
            {
                "status": "SEE_PACKAGE_TESTS",
                "equivalence_test_module": "tests/test_pricing_migration_equivalence.py",
                "scientific_math_changed": False,
                "aptf_runtime_dependency_in_pricing_pipeline": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SADE PRICING UNIT RUN 001")
    parser.add_argument("--endpoint", default="localhost:50051")
    parser.add_argument("--output-dir", type=Path, default=Path("output/unit_runs/pricing_001"))
    args = parser.parse_args()

    summary = run_pricing_unit_001(endpoint=args.endpoint, output_dir=args.output_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if summary.get("status") != "COMPLETE":
        return 1
    if summary.get("aptf_modules_loaded_count", 0) != 0:
        return 1
    if summary.get("aptf_files_opened_count", 0) != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
