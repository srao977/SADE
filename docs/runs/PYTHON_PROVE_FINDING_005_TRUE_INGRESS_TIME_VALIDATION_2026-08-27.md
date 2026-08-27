# Python-Prove Finding 005: True Ingress Time Validation

**Date:** August 27, 2026  
**Status:** PASS - RUNTIME LATENCY NOW MEASURABLE  
**Repository:** `C:\Users\chino\SADE`  
**Input:** Current unchanged SDX implementation, AAPL, 100 vectors

## Before Baseline

- Complete package tests: **31 passed, 0 failed**.
- Adaptive: 100 received, 15 initializing, 85 actionable.
- Decisions: 8 BUY, 10 SELL, 67 HOLD.
- Adaptive events: 331 adaptation, 170 feedback.
- Pricing: 85 derivative-ready, 55 F4-ready, 55 emissions, 18 domain exits.
- Confidence: 29 MEDIUM, 26 LOW.
- Colors: 33 AMBER, 14 GREEN, 8 RED.

Artifacts are under `output/python_prove/finding_005/before`.

## Before Defect Evidence

The controlled historical fixture produced:

```text
source_timestamp: 2000-01-01T00:00:00Z
event_time:       946684800.0
receive_time:     946684800.0
equal:            true
```

Executable code assigned `receive_time = event_time`. Evidence is in
`fabricated_receive_time_before.json`.

## Timestamp Capture And Propagation

Six focused tests pass. They prove:

- true UTC receive time differs from a controlled historical event time;
- source/event time is preserved exactly;
- direct normalizer calls capture real current UTC instead of source time;
- ingress UTC and monotonic tick are captured once;
- completion wall time follows ingress wall time;
- monotonic elapsed duration is nonnegative;
- observation ID and Adaptive mathematics remain unchanged when receive time changes;
- no production timing collection is retained;
- the machine timing contract freezes clocks, endpoints, units, and scientific exclusions.

All 100 integrated rows retained nonempty ingress time, valid wall-clock order, and
nonnegative elapsed duration. Receive-time propagation failures: **0**.

## Scientific And Identity Equivalence

Adaptive field comparison: **PASS**. All 32 source/scientific/output fields have
zero mismatches across 100 rows. `observation_id` is exact for every row. Expected
differences are receive/completion clocks, elapsed timing, and execution-instance
`emission_id`. Emission IDs remain nonempty with unchanged generation code.

Pricing field comparison: **PASS**. All 14 prior integrated scientific and
categorical fields have zero mismatches. Pricing summaries match after excluding
only generation and new runtime fields. Migration-equivalence evidence is exact.

## Measured Local Latency

The primary final-output metric is `ingress_to_pricing_output_elapsed_ns`.

| Statistic | Adaptive output | Pricing output |
|---|---:|---:|
| Count | 100 | 100 |
| Minimum | 401,300 ns | 424,700 ns |
| Mean | 609,700 ns | 1,067,561 ns |
| Median / p50 | 595,000 ns | 1,272,450 ns |
| p95 | 738,200 ns | 1,599,645 ns |
| p99 | 859,038 ns | 1,785,333.0000000014 ns |
| Maximum | 862,800 ns | 2,065,800 ns |

These are local validation-run observations, not a production benchmark or SLA.
The p99 decimal is NumPy's interpolated percentile result.

The separate 10,000-sample clock-measurement loop reported 73.68 ns mean and 100 ns
median for three `perf_counter_ns` calls plus Python list append. It is an approximate
validation-harness overhead measure, not an isolated hardware clock benchmark.

## Longer Run

A 1,000-observation deterministic local replay completed with timing enabled:

- Adaptive latency samples valid: 1,000.
- Pricing latency samples valid: 1,000.
- receive-time propagation failures: 0.
- production-retained latency samples: 0.
- six default Adaptive diagnostic/output histories: all 0.
- Pricing history size/bound: 31/31.

The validation harness may retain its explicitly bounded samples to calculate
percentiles; production pipelines do not.

## After Tests And Runs

- Complete package tests: **37 passed, 0 failed**.
- Adaptive unchanged-SDX run: PASS with the same science and decisions.
- Integrated Pricing unchanged-SDX run: PASS with the same science and categories.
- Timestamp capture and propagation: PASS.
- Observation identity: PASS.
- Emission identity semantics: PASS.

## Prior Finding Regressions

- Finding 001: **PASS**, 2 focused tests; analytic production, no production RK45,
  analytic/reference equivalence preserved.
- Finding 002: **PASS**, 2 focused tests; active-index fitting and exact reference
  equivalence preserved.
- Finding 003: **PASS**, established 1,000-row validator; bounded histories preserved.
- Finding 004: **PASS**, 8 focused tests; 55-case corpus exact, `ddof=0`, condition
  semantics, and thresholds preserved.

## Latency Scope

This finding measures local SADE ingress-to-output processing. It does not measure
provider latency, historical event age as network latency, Azure Event Hub delay,
network transit, SADE_Go latency, order latency, or a production end-to-end SLA.

## Integrity

```text
SDX MODIFIED: NO
SOURCE/EVENT TIME SEMANTICS MODIFIED: NO
TRUE RECEIVE_TIME ADDED: YES
FABRICATED receive_time = event_time REMOVED: YES
OBSERVATION_ID GENERATION MODIFIED: NO
EMISSION_ID GENERATION MODIFIED: NO
SCIENTIFIC MATHEMATICS MODIFIED: NO
FINDING 001 MODIFIED: NO
FINDING 002 MODIFIED: NO
FINDING 003 RETENTION REGRESSED: NO
FINDING 004 F4 CONTRACT MODIFIED: NO
UNBOUNDED TELEMETRY ADDED: NO
GO CODE CREATED: NO
EVENT HUB CODE CREATED: NO
SADE_GO IMPLEMENTED: NO
```

## Artifacts

Machine-readable evidence is under `output/python_prove/finding_005`:

- `fabricated_receive_time_before.json`
- `runtime_timing_contract.json`
- `receive_time_validation.json`
- `timestamp_propagation.json`
- `latency_measurements.jsonl`
- `latency_summary.json`
- `before/` and `after/`
- `long_run/latency_boundedness.json`
- `comparisons/adaptive_before_after.json`
- `comparisons/pricing_before_after.json`
- `comparisons/finding_001_regression.json`
- `comparisons/finding_002_regression.json`
- `comparisons/finding_003_regression.json`
- `comparisons/finding_004_regression.json`
- `comparisons/integrity_summary.json`
- `comparisons/finding_005_closeout.json`

## Final Status

**RESOLVED - RUNTIME LATENCY NOW MEASURABLE**

Finding 005 makes local SADE runtime duration measurable with genuine clock endpoints.
No Go, Event Hub, or SADE_Go work was started.
