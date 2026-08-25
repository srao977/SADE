"""
Module/File Name: sade/unit_run/run_001.py
Date Created / Migrated: August 25, 2026
Purpose:
    Execute SADE Unit Run 001 with independence instrumentation.
Executive Overview:
    Runs AAPL/100 via SADE pipeline and records loaded module paths plus file
    open events to prove zero runtime dependency on APTF.
Role in SADE:
    Validation harness for V0.1 acceptance gate.
Inputs:
    Optional endpoint/output_dir arguments.
Outputs:
    Unit run summary with independence counters.
Parameters / Configuration:
    endpoint and output_dir.
Persistent State:
    audit event lists during process runtime.
External Dependencies:
    sade.adaptive_pipeline
Main Callers / Consumers:
    Implementation validation and docs/run reporting.
Important Assumptions:
    The process can register a Python audit hook for file-open tracking.
Scientific Provenance:
    Originated from the validated frozen Test 006B adaptive execution lineage.
Explicit Exclusions / What This Module Does NOT Do:
    - No scientific formula mutation
    - No external fallback imports
Failure / Error Behavior:
    Returns nonzero when pipeline run fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sade.adaptive_pipeline import AdaptivePipeline, AdaptivePipelineConfig, DEFAULT_UNIT_RUN_OUTPUT_DIR


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


def run_unit_001(endpoint: str = "localhost:50051", output_dir: Path = DEFAULT_UNIT_RUN_OUTPUT_DIR) -> dict[str, Any]:
    """Run SADE Unit Run 001 (AAPL/100) with independence auditing."""
    opened_files: list[str] = []

    def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and args:
            opened_files.append(str(args[0]))

    sys.addaudithook(_audit_hook)

    config = AdaptivePipelineConfig(
        entity="AAPL",
        max_vectors=100,
        sdx_endpoint=endpoint,
        output_dir=output_dir,
    )

    with AdaptivePipeline(config=config) as pipeline:
        summary = pipeline.run()

    evidence = _collect_apft_dependency_evidence(opened_files)
    summary.update(evidence)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "unit_run_001_with_independence_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SADE Unit Run 001")
    parser.add_argument("--endpoint", default="localhost:50051")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_UNIT_RUN_OUTPUT_DIR)
    args = parser.parse_args()

    summary = run_unit_001(endpoint=args.endpoint, output_dir=args.output_dir)
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
