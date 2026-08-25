# SADE PRICING UNIT RUN 001 (AAPL / 100) - Run Report (2026-08-25)

## Run Identity
- run_id: SADE_PRICING_UNIT_RUN_001
- entity: AAPL
- vectors_requested: 100
- endpoint: localhost:50051
- command: python -m sade.unit_run.run_pricing_001 --endpoint localhost:50051 --output-dir output/unit_runs/pricing_001

## Outcome
- status: COMPLETE
- vectors_received: 100
- adaptive.initializing: 15
- adaptive.actionable: 85
- adaptive.BUY: 8
- adaptive.SELL: 10
- adaptive.HOLD: 67
- source_timestamp_first: 2022-09-30 04:00:00
- source_timestamp_last: 2022-09-30 06:21:00

## Artifact Manifest

| Artifact | Path |
|---|---|
| Observation stream export | output/unit_runs/pricing_001/observations.csv |
| Unit summary | output/unit_runs/pricing_001/pricing_summary.json |
| Equivalence marker | output/unit_runs/pricing_001/migration_equivalence.json |

## Runtime Independence Checks
- aptf_modules_loaded_count: 0
- aptf_files_opened_count: 0
- timestamp_normalization: false
- cadence_logic_added: false

## Structured Metrics Snapshot
- adaptive.initializing: 15
- adaptive.actionable: 85
- adaptive.BUY: 8
- adaptive.SELL: 10
- adaptive.HOLD: 67
- pricing.observations_received: 100
- pricing.warmup_observations: 45
- pricing.derivative_ready_observations: 85
- pricing.f4_ready_observations: 55
- pricing.rk45_attempts: 55
- pricing.rk45_successes: 55
- pricing.rk45_failures: 0
- pricing.price_emissions_generated: 55
- pricing.price_cockpit_outputs: 55

## Pre-Run Package Validation
- pytest -q => 16 passed in 1.30s

## Interpretation
The integrated runtime completed end-to-end with live SDX data. Adaptive and pricing both emitted non-degenerate outputs, and pricing produced 55 emissions with 55 successful RK45 solves.

## Rerun Procedure
1. Start or point to an available SDX endpoint.
2. Execute:
   python -m sade.unit_run.run_pricing_001 --endpoint <sdx-host:port> --output-dir output/unit_runs/pricing_001
3. Confirm in pricing_summary.json:
   - status == COMPLETE
   - vectors_received == 100
   - aptf_modules_loaded_count == 0
   - aptf_files_opened_count == 0

## Final Integrity Statement
SADE pricing migration is scientifically and behaviorally validated by package tests, migration-equivalence tests, and a successful live integrated SDX run for AAPL/100.
