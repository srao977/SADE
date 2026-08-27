# Python-Prove Finding 001 Analytic Solve Validation

**Date:** August 27, 2026  
**Status:** RESOLVED - BLOCKER REMOVED  
**Repository:** `C:\Users\chino\SADE`  
**Input:** unchanged SDX at `localhost:50051`, entity AAPL, 100 vectors

## Purpose

Record the before, candidate, downstream shadow, attempted after, integrity, and final
production decision for Finding 001 only.

## Before Baseline

- Package tests: `16 passed`, `0 failed`.
- Adaptive run: COMPLETE, 100 received, 15 initializing, 85 actionable, 331 adaptation
  events, 170 feedback events, BUY 8, SELL 10, HOLD 67.
- Integrated Pricing run: COMPLETE, 55 projection attempts, 55 successes, 0 failures,
  18 domain exits, and 55 PriceEmission/cockpit outputs.
- Before artifacts were written beneath `output/python_prove/finding_001/before/` and
  hashed in `before/artifact_hashes.json`.

The first Adaptive attempt failed with connection refused because SDX was not running.
The existing unchanged SDX server was then started with `go run ./cmd/sdx-server`, and
the authoritative before run was repeated successfully into the same dedicated area.

## RK45 Reference Capture

The reference corpus contains 55 solves and records source identity, sequence, initial
state, $A$, $b$, standardized and physical coefficients, means/scales/envelope, interval,
grid, `rtol`, component `atol`, all 11 trajectory points, terminal state, `nfev`, message,
success, sampled exit data, and `D_local_maximum`.

Reference settings:

- `scipy.integrate.solve_ivp`
- `method="RK45"`
- `t_span=(0.0, 1.0)`
- `t_eval=np.linspace(0.0, 1.0, 11)`
- `rtol=1e-6`
- component `atol` as captured per solve

## Analytic Self-Validation

All checks passed for every eligible solve:

- solution at $\Delta t=0$ equals $y_0$;
- augmented constant component remains exactly 1;
- candidate output is finite;
- repeated identical input is bit-deterministic;
- small-$\Delta t$ difference quotient agrees with $Ay_0+b$.

## Tolerance Policy

For component $k$ and sampled time $i$:

$$
|y^{RK45}_{ik}-y^{expm}_{ik}|
\le 10\left(atol_k+rtol\max(|y^{RK45}_{ik}|,|y^{expm}_{ik}|)+\epsilon_{64}\right).
$$

This uses the frozen component-specific RK45 absolute tolerance, frozen relative
tolerance, actual state magnitude, IEEE-754 float64 epsilon, and a 10x local-to-global
safety factor over the fixed one-minute interval. The observed maximum ratio to this
bound was `0.04956354480731912`; the tolerance was not loosened after measurement.

## RK45 Versus Analytic Results

- Solves compared: 55.
- Trajectory points compared: 605.
- Maximum absolute error `p`: `1.621765477466397e-08`.
- Maximum absolute error `p1`: `9.312251400550586e-09`.
- Maximum absolute error `p2`: `5.339989454095084e-09`.
- Maximum relative error `p`: `1.1307053004770815e-10`.
- Maximum relative error `p1`: `1.4777308649677203e-06`.
- Maximum relative error `p2`: `2.4010100479304756e-05`.
- Maximum terminal absolute errors `[p,p1,p2]`:
  `[5.962476734566735e-09, 3.4190666270417225e-09, 1.9605112255849377e-09]`.
- Domain exit: exact PASS.
- First exit time: exact PASS.
- Exit dimension: exact PASS.
- Maximum `D_local_maximum` difference: `5.79502066777593e-07`, PASS.

## Downstream Shadow Comparison

The same already-computed fit, state, envelope, and metadata fed both trajectories.
The analytic trajectory then passed through the existing numerical payload contract,
PriceEngine policy, PolicyState progression, PriceEmission, cockpit interpreter, and
CockpitState progression.

- PriceEmission categorical equivalence: PASS.
- PolicyState equivalence: PASS.
- Cockpit categorical and state equivalence: PASS.
- Pricing integrated observations and normalized summary: PASS.

## Historical Attempted After Validation

- Package tests after candidate switch: `16 passed`, `0 failed`.
- Adaptive run completed with the same scientific values and summary counts.
- Integrated Pricing run completed with all recorded rows and normalized summary exact.
- Production was restored to RK45 after the mandatory Adaptive exact-ID gate failed.
- Final package tests after restoration: recorded in the completion summary.

## First Divergence

The first difference is Adaptive row 0 field `emission_id`:

- Before: `0e2756cddafd41c45c25176ea124100dc633ab0ef02b10d9332024bcfd38b35f`
- After: `3fd5390bd3aeab488c75fb84503045b6e401114699a03995da914aef1e665461`

All 100 `emission_id` values differ. No other Adaptive CSV field differs, and normalized
Adaptive summaries match exactly. Existing `AdaptiveEmitter` computes `emission_id` by
hashing a payload containing `lifecycle_start_ns`, `lifecycle_end_ns`,
`direct_lifecycle_ns`, and component lifecycle timings sourced from
`time.perf_counter_ns()`. Thus byte-identical repeat-run IDs are not achievable under
the current implementation. Altering that behavior is explicitly outside Finding 001.

## Historical Production-Switch Decision

The earlier decision was **DO NOT SWITCH**. The trajectory and downstream scientific gates passed, but the task
requires exact Adaptive IDs and directs an immediate stop on any Adaptive difference.
Production `solve_cover` therefore remained the frozen RK45 implementation at that
checkpoint, and Finding 001 was marked `NOT RESOLVED` pending human review.

This section is retained as historical evidence. The invalid ID criterion was corrected
and the final switch decision is recorded below.

## Integrity Checks

- SDX modified: NO.
- Adaptive scientific code modified: NO.
- `causal_quadratic` modified: NO.
- `fit_f4` modified: NO.
- Pricing history behavior modified: NO.
- Unbounded collections modified: NO.
- ODE equations modified: NO.
- F4 mathematics modified: NO.
- RK45 reference mathematics modified: NO.
- Production solution method changed: NO.
- Production RK45 execution removed: NO.
- `solve_cover` removed: NO.
- Go code created: NO.
- Volume modified: NO.
- Decision Engine modified: NO.

## Machine-Readable Evidence

- `before/rk45_reference.json`
- `candidate/analytic_candidate.json`
- `candidate/analytic_self_validation.json`
- `comparisons/rk45_vs_analytic.json`
- `comparisons/downstream_shadow_equivalence.json`
- `comparisons/adaptive_before_after.json`
- `comparisons/pricing_before_after.json`
- `comparisons/integrity_summary.json`

All paths above are relative to `output/python_prove/finding_001/`.

## Final Closeout Validation

### Corrected Deterministic-Field Policy

| Field category | Classification | Final comparison rule |
|---|---|---|
| Source order, timestamp, OHLCV, status, D01/D02/D04-derived values, Adaptive decisions/state, counts | A. Scientific/deterministic | Exact equality |
| `lifecycle_start_ns`, `lifecycle_end_ns`, `direct_lifecycle_ns`, component durations | B. Execution-instance telemetry | Valid shape/presence; bytes need not match |
| `emission_id` | C. Derived ID from execution-instance telemetry | Per-run semantic integrity, not cross-run bytes |
| `observation_id` | A. Deterministic source lineage | Exact cross-run equality |
| Unknown differing fields | D. Unknown | Investigate; none were found |

All 32 deterministic fields present in the Adaptive observations artifact matched
exactly across 100 rows. Normalized scientific and independence summaries also matched.

### Emission and Observation ID Validation

For both the frozen before run and final post-switch run:

- emissions: 100;
- non-empty emission IDs: 100;
- unique emission IDs: 100;
- duplicate emission IDs: 0;
- non-empty observation IDs: 100;
- unique observation IDs: 100;
- source lineage complete: YES.

`observation_id` matched exactly for all 100 rows. ID-generation code changed: NO.

### Rerun Analytic Comparison

The post-switch production analytic path was compared with the frozen RK45 reference:

- solves: 55;
- trajectory points: 605;
- maximum absolute errors `[p,p1,p2]`:
  `[1.621765477466397e-08, 9.312251400550586e-09, 5.339989454095084e-09]`;
- maximum relative error: `2.4010100479304756e-05`;
- maximum tolerance ratio: `0.04956354480731912`;
- domain exit, first exit, exit dimension: exact PASS;
- `D_local_maximum`: PASS, maximum difference `5.79502066777593e-07`;
- PriceEmission: PASS;
- PolicyState: PASS;
- cockpit output/state: PASS.

The tolerance policy was unchanged.

### Post-Switch Runs

- Package tests: `17 passed`, `0 failed`.
- Runtime no-RK45 guard: PASS.
- Adaptive unit run: COMPLETE, 100 received, deterministic scientific/state PASS.
- Integrated Pricing run: COMPLETE, 55 emissions, 18 domain exits, summary PASS.
- Production analytic versus frozen RK45 reference: PASS.

The integrated artifact retains historical `rk_success` and `rk45_*` names as legacy
compatibility labels for generic projection success. They do not indicate RK45 execution.

### Final Machine-Readable Evidence

- `comparisons/corrected_adaptive_equivalence.json`
- `comparisons/emission_id_semantic_validation.json`
- `comparisons/production_analytic_vs_rk45_reference.json`
- `comparisons/final_pricing_equivalence.json`
- `comparisons/finding_001_closeout.json`
- `closeout/after/artifact_hashes.json`

### Final Integrity

- SDX modified: NO.
- Adaptive scientific code modified: NO.
- Emission/observation ID generation modified: NO.
- `causal_quadratic` / `fit_f4` modified: NO.
- Unbounded state modified: NO.
- ODE equations/domain logic modified: NO.
- Production solution method: ANALYTIC EXPM.
- Production RK45 executed: NO.
- RK45 retained: REFERENCE ONLY.
- Go code created: NO.
- Finding 002 started: NO.

## Final Result

**PASS - RESOLVED, BLOCKER REMOVED.** Stop for human review. Do not begin Finding 002.