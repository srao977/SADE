# Python-Prove Finding 005: True Ingress Time Implementation

**Date:** August 27, 2026  
**Status:** IMPLEMENTED, PENDING FINAL HUMAN REVIEW  
**Repository:** `C:\Users\chino\SADE`  
**Finding:** Fabricated receive time and unmeasurable local runtime latency

## Purpose

Introduce a genuine SADE ingress timestamp and valid local elapsed-time endpoints
without changing source time, scientific mathematics, identities, SDX, or the
accepted Findings 001-004 behavior.

## Scope

This change captures one timezone-aware UTC wall timestamp and one monotonic tick
when an SDX vector first reaches `AdaptivePipeline.process_vector`. It propagates
the wall timestamp through normalization and external artifacts, and measures
ingress-to-Adaptive-output and ingress-to-Pricing-output durations. Telemetry is
operational only and no sample history is retained in production objects.

## Executive Summary

- True SADE ingress boundary: `sade.adaptive_pipeline.pipeline.AdaptivePipeline.process_vector`.
- UTC clock: `datetime.now(timezone.utc)` serialized as ISO-8601 with `Z`.
- Elapsed clock: `time.perf_counter_ns()`.
- Source/event timestamp remains exactly the SDX `source_timestamp`.
- `receive_time = event_time` was removed from `normalizer.py`.
- Direct lower-level normalization without an ingress value captures current UTC;
  it never falls back to event time.
- `observation_id` and `emission_id` hash implementations are unchanged.
- Receive time is not used by D01, D02, D04, Adaptive decisions, Pricing science,
  F4, projection, PriceEngine, or cockpit.

## Timestamp Lineage Before

```text
SDX MarketVector.source_timestamp
    -> AdaptivePipeline.build_source_row.event_timestamp_utc
    -> SourceRowNormalizer.event_time
    -> receive_time = event_time                 DEFECT
    -> NormalizedObservation
    -> D01 event-time calculations
    -> Adaptive output source_timestamp
    -> Pricing source_timestamp
```

A controlled source timestamp of `2000-01-01T00:00:00Z` produced both
`event_time=946684800.0` and `receive_time=946684800.0`. Executable inspection
proved this was assignment, not clock coincidence.

## True Ingress Boundary

The SDX client yields each gRPC `MarketVector` to the caller. The earliest practical
application-owned point after that yield and before validation or science is entry
to `AdaptivePipeline.process_vector`. The method captures:

```python
receive_monotonic_ns = time.perf_counter_ns()
receive_time_utc = datetime.now(timezone.utc)
```

The clocks are wrapped only by narrow module-local functions to permit deterministic
tests. The values are captured once and passed forward; downstream stages do not
recapture or overwrite ingress time.

## Clock Selection

`receive_time_utc` is an epoch-bearing, timezone-aware wall clock suitable for
artifact correlation. `receive_monotonic_ns` has no wall-clock meaning and is used
only as the start tick for same-process elapsed durations. Wall and monotonic clocks
are not subtracted from each other.

## Implementation Change

`build_source_row` accepts the already captured ingress UTC value and preserves the
incoming `event_timestamp_utc`. `SourceRowNormalizer` parses these independently:

- `event_time` from `event_timestamp_utc`;
- `receive_time` from `receive_time_utc`.

If lower-level code invokes the normalizer without `receive_time_utc`, the normalizer
captures current timezone-aware UTC. It does not fabricate telemetry from event time.

The Adaptive row adds:

- `receive_time_utc`;
- `receive_monotonic_ns`;
- `processing_complete_time_utc`;
- `ingress_to_adaptive_output_elapsed_ns`.

The integrated Pricing artifact propagates the same `receive_time_utc` and adds its
own completion UTC and `ingress_to_pricing_output_elapsed_ns`.

## Source/Event Time Preservation

`source_timestamp` and `event_timestamp_utc` are not regenerated, rounded, shifted,
or replaced. D01 continues to calculate model delta and model time exclusively from
`NormalizedObservation.event_time`. D04 evaluation time also remains event time.
The causal one-observation lag and Pricing timestamp behavior are unchanged.

## Identity Isolation

`observation_id` remains the SHA-256 of physical/source row identity, event timestamp,
and OHLCV. Receive time is excluded. A controlled test varies receive time while
holding source input fixed and requires exact observation ID and mathematics.

`emission_id` generation code is unchanged. It still includes the existing
execution-instance emitter lifecycle timing surface; the new ingress fields were not
added to `emission_core` or its hash.

## Latency Metrics

| Metric | Start | End | Clock | Unit |
|---|---|---|---|---|
| `ingress_to_adaptive_output_elapsed_ns` | `process_vector` entry after gRPC yield | flattened Adaptive record constructed | `perf_counter_ns` | ns |
| `ingress_to_pricing_output_elapsed_ns` | same ingress monotonic tick | `PricingPipeline.process` returned and integrated record ready | `perf_counter_ns` | ns |

`processing_complete_time_utc >= receive_time_utc` is checked only between comparable
UTC clocks. Monotonic elapsed values are independently required to be nonnegative.

For historical SDX replay, `receive_time_utc - event_time` is replay age. It is not
network or transport latency. The valid Finding 005 measurements begin at real SADE
ingress and end at local output completion.

## Bounded Telemetry Strategy

Per-row timing is returned and externally streamed to finite validation artifacts.
Adaptive production summary retains only count, minimum, maximum, and running sum
for mean. It retains no timing list. Existing diagnostic/output histories remain
empty by default. Exact percentiles are calculated only by the explicit validation
harness from its bounded 100/1,000-row samples.

## Findings 001-004 Preservation

- Finding 001: analytic EXPM production projection and RK45 reference preserved.
- Finding 002: active-index derivative and F4 scheduling preserved.
- Finding 003: zero default diagnostic/output retention and 31-row Pricing bound preserved.
- Finding 004: population `ddof=0`, normal equations, condition semantics, thresholds,
  and the 55-case golden corpus preserved.

## Future SADE_Go/Event Hub Mapping

A future real-time ingress may preserve source/event time and Event Hub metadata,
then independently capture SADE_Go ingress time at the future IO-vector publisher
boundary. That design can use an epoch UTC timestamp for correlation and a monotonic
tick for local durations. Finding 005 does not implement Go, IO_Vector, Event Hubs,
or Azure infrastructure.

## Scientific Non-Change Statement

```text
Event/Source Time: scientific/provenance timestamp
Receive/Ingress Time: operational runtime timestamp
Clock: datetime.now(timezone.utc) + time.perf_counter_ns()
Scientific Mathematics Changed: NO
Scientific Model Uses Receive Time: NO
Latency Telemetry: OPERATIONAL ONLY
```

## Explicit Exclusions

No SDX, protobuf, gRPC service, source data, D01/D02/D04 mathematics,
Adaptive decision rules, causal quadratic, F4, projection, PriceEngine, cockpit,
identity generation, Go, Event Hub, Volume Pipeline, Decision Engine, or Azure code
was changed or created.
