# SADE System Design V0.1 (2026-08-25)

## 1. Objective

Create an independent SADE repository runtime that executes the validated adaptive scientific lineage through SDX V1.1 input, with zero runtime dependency on APTF paths.

## 2. Scope and Capability

Current product capability in V0.1:
- Adaptive Pipeline only.
- One causal streaming path: SDX MarketVector -> SADE mapping -> AdaptiveEmitter -> observations and summary outputs.

Explicit exclusions in V0.1:
- D03 execution.
- Price/Volume engines.
- Stateful legacy TradingEnvelope runtime.
- Semantic input layer and paper execution components.

## 3. Runtime Architecture

1. Input boundary
- `sade.input.sdx_client.SadeSdxClient` consumes SDX V1.1 gRPC stream.
- Required vector fields: entity_id, source_row_index, source_timestamp, open, high, low, close, volume.

2. Orchestration boundary
- `sade.adaptive_pipeline.pipeline.AdaptivePipeline` validates strict entity/order, maps source records, and invokes emitter stepwise.
- Physical row compatibility mapping remains `physical_row = source_row_index + 2`.

3. Scientific execution boundary
- `sade.adaptive_emitter.emitter.AdaptiveEmitter.process` executes:
  - D01: `sade.d01.v02.model.D01V02Model.step`
  - D02: `sade.d02.v02.builder.build_return_shape`
  - D04 capturability: `sade.d04.envelope.capturability_model.CapturabilityModelV0_2.evaluate`
- Decision path emits BUY/SELL/HOLD only after initialization window completion.

4. Output boundary
- `observations.csv` with flattened immutable per-observation record.
- `summary.json` with aggregate metrics.
- Unit run adds independence counters to `unit_run_001_with_independence_summary.json`.

## 4. Provenance and Freeze Semantics

Scientific lineage source is the validated frozen adaptive path from prior APTF validation (006B lineage), migrated into SADE package ownership.

SADE-owned baseline identity source:
- `sade.configuration.scientific_baseline.get_baseline_fingerprints()`.

## 5. Independence Design Controls

1. Import ownership
- Runtime imports use `sade.*` package namespace only.

2. Local generated bindings ownership
- SDX generated stubs loaded from `sade/input/generated/sdx/v1`.

3. Runtime dependency instrumentation
- Unit run hooks Python audit events for file-open calls.
- Unit run scans loaded module paths in `sys.modules`.
- Acceptance condition: zero modules/files resolved under APTF root at runtime.

## 6. Validation Acceptance Criteria

Required acceptance conditions for SADE Unit Run 001:
- Status COMPLETE.
- vectors_received = 100 and vectors_requested = 100.
- INITIALIZING = 15, ACTIONABLE = 85, first_actionable = 16.
- Non-degenerate decisions (BUY, SELL, HOLD all represented).
- Runtime APTF dependency counters both equal zero.

## 7. Risks and Boundaries

- Emission IDs are lifecycle-time influenced and not the primary deterministic equivalence gate.
- Deterministic overlap is evaluated using stable scientific/decision fields and summary metrics.
