"""
Module/File Name: sade/__main__.py
Date Created / Migrated: August 25, 2026
Purpose:
    Provide minimal SADE CLI for running Adaptive Pipeline unit runs.
Executive Overview:
    Supports `python -m sade run --entity ... --max-vectors ...` to execute
    SADE V0.1 pipeline and persist SADE-owned outputs.
Role in SADE:
    Product runtime command entrypoint.
Inputs:
    CLI arguments.
Outputs:
    Console summary and unit-run files.
Parameters / Configuration:
    Entity, max vectors, endpoint, timeout, output directory.
Persistent State:
    None.
External Dependencies:
    sade.adaptive_pipeline
Main Callers / Consumers:
    Human operators and automation scripts.
Important Assumptions:
    SDX endpoint is reachable when live run is expected.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No scientific model definition
    - No APTF fallback behavior
Failure / Error Behavior:
    Returns nonzero exit code if pipeline status is FAILED.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sade.adaptive_pipeline import AdaptivePipeline, AdaptivePipelineConfig, DEFAULT_UNIT_RUN_OUTPUT_DIR
from sade.unit_run.run_pricing_001 import run_pricing_unit_001


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="sade", description="SADE V0.1 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run SADE adaptive pipeline")
    run.add_argument("--entity", default="AAPL")
    run.add_argument("--max-vectors", type=int, default=100)
    run.add_argument("--endpoint", default="localhost:50051")
    run.add_argument("--timeout-seconds", type=float, default=60.0)
    run.add_argument("--output-dir", type=Path, default=DEFAULT_UNIT_RUN_OUTPUT_DIR)

    pricing = sub.add_parser("run-pricing-001", help="Run SADE PRICING UNIT RUN 001")
    pricing.add_argument("--endpoint", default="localhost:50051")
    pricing.add_argument("--output-dir", type=Path, default=Path("output/unit_runs/pricing_001"))

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "run-pricing-001":
        summary = run_pricing_unit_001(endpoint=args.endpoint, output_dir=args.output_dir)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary.get("status") == "COMPLETE" else 1

    if args.command != "run":
        raise RuntimeError("UNSUPPORTED_COMMAND")

    config = AdaptivePipelineConfig(
        entity=args.entity,
        max_vectors=args.max_vectors,
        sdx_endpoint=args.endpoint,
        timeout_seconds=args.timeout_seconds,
        output_dir=args.output_dir,
    )
    with AdaptivePipeline(config=config) as pipeline:
        summary = pipeline.run()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("status") == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
