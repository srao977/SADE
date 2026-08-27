# Python-Prove Finding 001 Analytic Solve Implementation

**Date:** August 27, 2026  
**Status:** RESOLVED - BLOCKER REMOVED  
**Repository:** `C:\Users\chino\SADE`  
**Scope:** Finding 001 only

## Purpose

Investigate the executable `solve_cover` path, prove its ODE, implement an exact
affine matrix-exponential candidate beside the frozen RK45 reference, and change
production only if every required validation gate passes.

## Executive Summary

Executable inspection confirms that the production call uses a three-dimensional,
constant-coefficient affine ODE. The augmented-state `scipy.linalg.expm` implementation
passed direct trajectory and downstream comparison for all 55 projection-ready
observations. The prior cross-run byte-equality gate for `emission_id` was corrected:
the ID hashes `time.perf_counter_ns()` lifecycle telemetry and is an execution-instance
identifier, not deterministic scientific state. Every deterministic Adaptive field,
including source-derived `observation_id`, remains exact, while each run's emission IDs
are non-empty, unique, count-complete, and internally linked to source observations.

**Production switch decision:** YES. `solve_cover` now uses analytic `scipy.linalg.expm`;
the unchanged RK45 implementation is `solve_cover_rk45_reference` and validation-only.

## solve_cover Responsibility Decomposition

| Responsibility | Input | Output | Downstream consumer | Scientific | RK45-specific | Must survive analytic implementation |
|---|---|---|---|---|---|---|
| Select observations and batch up to 1024 | observation indices | groups | solver setup | No | No | Yes |
| Construct initial state | `p`, `p1`, `p2`, indices | flattened `[p,p1,p2]` | solver | Yes | No | Yes |
| Select model coefficients | standardized beta, means, scales | fixed local dynamics | vector field | Yes | No | Yes |
| Construct time grid | fixed `[0,1]`, 11 points | `t_eval` | solver and exit analysis | Yes | No | Yes |
| Construct component tolerances | `rtol`, scales, epsilon | flattened `atol` | RK45 | No | Yes | Reference only |
| Evaluate vector field | time, state, coefficients | state derivative | RK45 | Yes | No | Equation must survive |
| Generate trajectory | ODE, state, interval, grid | sampled trajectory | trajectory analysis | Yes | Yes | Replaceable operation |
| Check finite/success state | solver result | failure or trajectory | packaging | Yes | Partly | Generic success must survive |
| Reject extreme terminal displacement | terminal and initial state, scales | `NUMERICALLY_UNSTABLE` | pipeline | Yes | No | Yes |
| Compute local distance | trajectory, means, scales | `D_local_maximum` | numerical row | Yes | No | Yes |
| Test sampled envelope membership | trajectory, minima, maxima | inside mask | exit analysis | Yes | No | Yes |
| Find first sampled exit | inside mask and grid | exit time/dimension | numerical row | Yes | No | Yes |
| Package result | trajectory and diagnostics | solved/failed maps | numerical assembly | Yes | Partly | Scientific fields survive |
| Report `nfev` and RK45 message | solver object | diagnostics | no production consumer | No | Yes | No fabricated values |
| Recursively split failed batches | failed group | smaller reference solves | reference failure handling | No | Yes | Not needed by independent analytic solves |

## Executable Call Chain

```text
SDX StreamVectors
  -> AdaptivePipeline.process_vector
  -> PricingPipeline.process
     -> causal_quadratic(times_minutes, p, derivative_window)
     -> construct jp from adjacent finite p2 values
     -> fit_f4(p, p1, p2, jp, f4_window, ridge_lambda)
     -> valid_fit(fit, active_index)
     -> solve_cover([active_index], fit, p, p1, p2,
                    time_term=False, rtol=1e-6, epsilon=config.epsilon)
     -> build_numerical_row
        -> eigenvalues and perturbation_amplification via scipy.linalg.expm(A)
     -> PriceEngine.observe
        -> EmissionPolicy.emit
        -> PriceEmission
     -> PriceCockpitInterpreter.observe
        -> PriceCockpitEmission and CockpitState
```

`solve_cover` returns `(solved, failed)`. `build_numerical_row` consumes trajectory
terminal state, `envelope_exit`, `D_local_maximum`, `first_exit_time`, and
`exit_dimension`. No production consumer reads `nfev` or the solver message.

## Exact Executable ODE

State ordering is:

$$
y=\begin{bmatrix}p & p_1 & p_2\end{bmatrix}^{T}.
$$

For standardized F4 coefficients $\beta=[\beta_0,\beta_p,\beta_{p1},\beta_{p2}]$,
means $\mu$, and scales $s$, existing code computes:

$$
j=\beta_0+\sum_{k=0}^{2}\beta_{k+1}\frac{y_k-\mu_k}{s_k}.
$$

The already-computed physical coefficients are:

$$
a_k=\frac{\beta_{k+1}}{s_k},\qquad
c=\beta_0-a^T\mu.
$$

Therefore:

$$
\dot y=Ay+b,
\quad
A=\begin{bmatrix}
0&1&0\\
0&0&1\\
a_p&a_{p1}&a_{p2}
\end{bmatrix},
\quad
b=\begin{bmatrix}0\\0\\c\end{bmatrix}.
$$

- State dimension: 3.
- Initial condition: `[p[index], p1[index], p2[index]]`.
- Integration interval: `[0.0, 1.0]` minute.
- Evaluation grid: `np.linspace(0.0, 1.0, 11)`.
- RK45 method: explicit `method="RK45"`.
- Relative tolerance: pipeline default `1e-6`.
- Absolute tolerances: `[rtol*s_p, min(rtol*s_p1, 0.1*epsilon), rtol*s_p2]`.
- Coefficients are selected before integration and do not mutate during a solve.
- No event callback exists. Domain exit is evaluated from sampled trajectory points.
- No nonlinear state term exists.
- Production passes `time_term=False`, so time does not appear explicitly.

The dormant `time_term=True` branch is explicitly time-dependent. The analytic
candidate rejects that branch rather than claiming constant-coefficient equivalence.
No direct executable caller passes `True`.

## Analytic Derivation

The affine term is retained with the augmented system:

$$
M=\begin{bmatrix}A&b\\0&0\end{bmatrix},\qquad
z_0=\begin{bmatrix}y_0\\1\end{bmatrix},\qquad
z(t)=\exp(Mt)z_0.
$$

Production returns the first three components of $z(t)$ at every existing
`t_eval` value. It uses `scipy.linalg.expm`, does not invert $A$, and does not alter
the ODE, coefficients, initial state, interval, or trajectory analysis.

## Code Changes

- `sade/pricing_pipeline/projection.py`: production `solve_cover` now uses
  `analytic_affine_trajectory`; the original code is retained unchanged as
  validation-only `solve_cover_rk45_reference`.
- `sade/unit_run/validate_finding_001.py`: added reproducible same-input trajectory,
  downstream shadow, self-validation, corrected Adaptive/ID semantics, artifact
  hashing, and closeout evidence.
- `tests/test_pricing_migration_equivalence.py`: retained explicit APTF/RK45 reference
  comparison and added analytic trajectory comparison.
- `tests/test_pricing_pipeline.py`: added a runtime guard that makes both `solve_ivp`
  and the RK45 reference raise while normal production Pricing still emits.
- `sade/pricing_pipeline/pipeline.py`: updated solver-role documentation only.

## RK45 Reference Strategy

`solve_cover_rk45_reference` contains the historical RK45 implementation and is called
only by tests and the Finding 001 harness. `PricingPipeline.process` imports and calls
only analytic `solve_cover`. There is no runtime solver selector.

## Explicit Exclusions

No changes were made to `causal_quadratic`, `fit_f4`, histories, unbounded collections,
Adaptive science, SDX, Go code, Volume, Decision Engine, source timing, or IDs.

## Scientific Non-Change Statement

- ODE equations changed: NO.
- F4 mathematics changed: NO.
- Adaptive model changed: NO.
- Production solution method changed: YES, RK45 to analytic matrix exponential.
- Domain/exit analysis changed: NO.
- PriceEngine/cockpit mathematics changed: NO.

## Known Limitations

- Existing `rk_success` and `rk45_*` summary names are legacy-compatible names for
  generic projection success and were not renamed.
- The analytic production implementation intentionally rejects `time_term=True`;
  no executable production caller uses that explicitly time-dependent branch.

## Human-Review Items

Finding 001 is complete. Stop for human review before beginning Finding 002.

## Final Closeout

### Validation-Gate Correction

**Previous gate:** byte-identical Adaptive `emission_id` across independent runs.

**Why invalid:** `emission_id` hashes the complete emission core, including
`lifecycle_start_ns`, `lifecycle_end_ns`, `direct_lifecycle_ns`, and per-component
durations derived from `time.perf_counter_ns()`.

**Corrected gate:** exact equality for all deterministic scientific/state fields plus
per-run validation that emission IDs are present, unique, count-complete, and linked to
valid deterministic observation/source lineage. ID-generation code was not changed.

### Final Production Call Path

```text
PricingPipeline.process
  -> solve_cover
    -> analytic_affine_trajectory
      -> scipy.linalg.expm(augmented_matrix * time)
    -> unchanged stability, domain, first-exit, D_local_maximum, and packaging
  -> build_numerical_row -> PriceEngine -> PriceEmission -> cockpit
```

A targeted test patches both `solve_ivp` and `solve_cover_rk45_reference` to raise;
normal production Pricing still emits successfully. Production therefore does not
execute RK45.

### No-Change Attestations

- D01 mathematics changed: NO.
- D02 mathematics changed: NO.
- D04 mathematics changed: NO.
- AdaptiveEmitter mathematics changed: NO.
- Emission/observation ID generation changed: NO.
- `causal_quadratic` changed: NO.
- `fit_f4` changed: NO.
- ODE equations changed: NO.
- Domain logic changed: NO.
- PriceEngine mathematics changed: NO.
- Cockpit mathematics changed: NO.
- Finding 002 included: NO.
- Unbounded-state correction included: NO.
- SDX modified: NO.
- Go code created: NO.

**Blocker-removal status:** RESOLVED - BLOCKER REMOVED.