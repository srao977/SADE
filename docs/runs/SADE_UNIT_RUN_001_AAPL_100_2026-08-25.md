# SADE Unit Run 001 (AAPL, 100 vectors) - 2026-08-25

## 1. Run Definition

- Run ID: SADE_UNIT_RUN_001
- Entity: AAPL
- Requested vectors: 100
- Endpoint: localhost:50051
- Working directory: C:/Users/chino/SADE
- Output directory: C:/Users/chino/SADE/output/unit_runs/001

## 2. Commands Executed

1. Package tests:
- `python -m pytest -q`

2. SDX server startup (separate terminal):
- `Set-Location C:/Users/chino/SDX`
- `go run ./cmd/sdx-server`

3. Unit run:
- `python -m sade.unit_run.run_001 --endpoint localhost:50051 --output-dir output/unit_runs/001`

## 3. Unit Run Result

Status:
- COMPLETE

Core counts:
- vectors_received: 100
- initializing: 15
- actionable: 85
- first_actionable: 16

Decisions:
- BUY: 8
- SELL: 10
- HOLD: 67

Directional/path distribution:
- DOWNWARD: 52
- UPWARD: 47
- FLAT: 1

Position state after distribution:
- FLAT: 15
- LONG: 34
- SHORT: 51

Capturability and factor ranges:
- H min/max: 1.0 / 1.0
- Q_G min/max: 0.0 / 1.0
- Q_S min/max: 0.2060837882716345 / 0.8099896733017667
- Q_R min/max: 0.2366891430678969 / 0.6806070267937718
- C min/max: 0.0 / 0.5091643749101453

Timing/cadence observations:
- source_delta_t_seconds min/max: 60.0 / 300.0
- irregular_source_time_gap_count: 28
- source_timestamp_preserved: true
- timestamp_normalization: false

Adaptation/feedback:
- adaptation_event_count: 331
- feedback_event_count: 170

Failures:
- failures: []

## 4. Runtime Independence Evidence

From `unit_run_001_with_independence_summary.json`:
- aptf_modules_loaded_count: 0
- aptf_files_opened_count: 0

Conclusion:
- RUNTIME APTF DEPENDENCY: NONE

## 5. Deterministic Overlap Validation Against APTF Baseline

Reference artifacts:
- APTF summary: `C:/Users/chino/APTF/post08242026_docs/implementations/APTF_ADAPTIVE_PIPELINE_AAPL_100_VALIDATION_SUMMARY_2026-08-25.json`
- APTF CSV: `C:/Users/chino/APTF/post08242026_docs/implementations/APTF_ADAPTIVE_PIPELINE_AAPL_100_VALIDATION_2026-08-25.csv`

Comparison outcomes:
- Observation CSV mismatch rows excluding `emission_id`: 0 of 100.
- Summary common-key mismatches (deterministic keys, metadata excluded): 0.

Conclusion:
- SCIENTIFIC MATHEMATICS CHANGE: NONE

## 6. Generated Artifacts

- `C:/Users/chino/SADE/output/unit_runs/001/observations.csv`
- `C:/Users/chino/SADE/output/unit_runs/001/summary.json`
- `C:/Users/chino/SADE/output/unit_runs/001/unit_run_001_with_independence_summary.json`
- `C:/Users/chino/SADE/output/unit_runs/001/migration_hash_evidence.json`

## 7. Acceptance Block

- SADE UNIT RUN 001 STATUS: PASS
- RUNTIME APTF DEPENDENCY: NONE
- SCIENTIFIC MATHEMATICS CHANGE: NONE
