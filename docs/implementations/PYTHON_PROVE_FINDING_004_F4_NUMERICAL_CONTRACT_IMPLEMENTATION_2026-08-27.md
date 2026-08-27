# Python-Prove Finding 004: F4 Numerical Contract Implementation

**Date:** August 27, 2026  
**Status:** IMPLEMENTED, PENDING FINAL HUMAN REVIEW  
**Repository:** `C:\Users\chino\SADE`  
**Finding:** `fit_f4` numerical migration risk

## Purpose

Convert the authoritative Python `fit_f4` behavior into an explicit, executable,
lossless migration contract without changing its scientific mathematics. This work
does not implement Go and does not improve or replace the existing normal equations.

## Scope

The only production edit is explicit `ddof=0` in both `fit_f4` and
`fit_f4_at_index`. Validation-only code captures the current inputs,
intermediates, results, and downstream categories for all eligible fits in the
accepted unchanged-SDX AAPL/100 run.

## Executive Summary

- F4 window: 30 rows ending at the active index.
- Input columns: `p`, `p1`, `p2`; target: `jp`.
- Standard deviation: population, `ddof=0`.
- Design columns: intercept, standardized `p`, standardized `p1`, standardized `p2`.
- Ridge: $\lambda=1.0$, slopes penalized, intercept unpenalized.
- Solve: ridge-adjusted normal equations through `np.linalg.solve`.
- Condition: `np.linalg.cond(design)`, not the normal matrix.
- Golden corpus: 55 self-contained, exact-float64 cases.
- Downstream condition thresholds: `<= 7.835779770603297` and
  `<= 13.040323846425492` in `EmissionPolicy.emit`.

## Executable Lineage

The current code path is:

```text
PricingPipeline._closes / _p1 / _p2 / _jp
    -> p / p1 / p2 / jp NumPy float arrays
    -> fit_f4_at_index(active_index, f4_window=30, ridge_lambda=1.0)
    -> standardized beta, physical coefficients, means, scales,
       minimum, maximum, condition
    -> allocate_fit row at active_index
    -> solve_cover
         physical -> affine analytic projection
         minimum/maximum -> envelope exit
    -> build_numerical_row
         physical -> eigenvalues and perturbation amplification
         condition -> numerical["condition_number"]
         standardized/means/scales -> local JSON fields
    -> PriceEngine.observe
    -> EmissionPolicy.emit
         condition_number -> confidence_state
    -> PriceEmission.condition_number / confidence_state / color
    -> PriceCockpitInterpreter.observe
         consumes PriceEmission confidence and other emission fields
    -> PriceCockpitEmission
```

The cockpit does not compare `condition_number` directly. It receives the resulting
`confidence_state`; with the current `low_confidence_requires_amber=False`, condition
can still affect cockpit output through the retained confidence field without being
the sole cockpit-color rule.

## Mathematical Contract

### Input window

For active index $i$ and window $N=30$:

$$
I = \{i-N+1,\ldots,i\}
$$

Production retains 31 synchronized rows because the newest row is pending while
the fit ends at `active_index = current_index - 1`. The fitted values matrix is:

$$
V = [p_I, p1_I, p2_I] \in \mathbb{R}^{30\times3},\qquad y=jp_I.
$$

`fit_f4_at_index` returns `None` if $i<N-1$, $i<0$, $i\ge len(p)-1$, or any target
in `jp[I]` is nonfinite.

### Means and population scales

Executable calls are `values.mean(axis=0)` and
`values.std(axis=0, ddof=0)`. For column $j$:

$$
\mu_j=\frac{1}{N}\sum_{k=1}^{N}V_{kj},\qquad
s_j=\sqrt{\frac{1}{N}\sum_{k=1}^{N}(V_{kj}-\mu_j)^2}.
$$

NumPy operates on production `float64` arrays. A fit is unavailable when any scale
is `<= 0` or when not all scales are finite. There is no epsilon, clamp, or special
near-zero guard: a positive finite near-zero scale is accepted exactly as before.

### Standardization and design

Operation order is `(values - means) / scales`. Let $Z$ be that standardized
matrix. The exact design construction is:

$$
X=[\mathbf{1},Z_p,Z_{p1},Z_{p2}]\in\mathbb{R}^{30\times4}.
$$

The intercept is first. The frozen column order is intercept, `p`, `p1`, `p2`.

### Ridge and normal equations

The ridge matrix and solve are:

$$
R=\operatorname{diag}(0,1,1,1),\qquad \lambda=1.0,
$$

$$
M=X^TX+\lambda R,\qquad r=X^Ty,\qquad
\beta=\operatorname{solve}(M,r).
$$

The exact executable multiplication order is `design.T @ design +
ridge_lambda * ridge` and `design.T @ jp[ids]`. The input to
`np.linalg.solve` is `(M, r)`. The intercept is not penalized. A
`np.linalg.LinAlgError` makes the active fit unavailable.

No QR, SVD, `lstsq`, or alternate solver is introduced.

### Beta and physical coefficients

`beta` has shape `(4,)` in the order standardized intercept, standardized `p`
slope, standardized `p1` slope, standardized `p2` slope. Physical slopes are
calculated first:

$$
a=\beta_{1:}/s.
$$

The physical vector is then:

$$
[b,a_p,a_{p1},a_{p2}]
=[\beta_0-a\cdot\mu,a_p,a_{p1},a_{p2}].
$$

### Extrema, condition, and validity

`minimum = values.min(axis=0)` and `maximum = values.max(axis=0)`.

The condition-number input is exactly the unregularized design matrix $X$:

```python
np.linalg.cond(design)
```

It is not $X^TX$ and not $X^TX+\lambda R$. NumPy's default is the 2-norm condition
through singular values. The normal-equation solve retains its known sensitivity,
but the reported policy input remains `cond(X)` because that is current science.

`valid_fit` is exactly `all(isfinite(standardized beta))`. The production
single-index helper expresses unavailable fits as `None` after the earlier input,
scale, or solve guards.

## Population Versus Sample Standard Deviation

For $N=30$, the population denominator is 30 and the Bessel-corrected sample
denominator is 29. For the same sum of squared deviations:

$$
\frac{s_{sample}}{s_{population}}=\sqrt{\frac{30}{29}}
=1.0170952554312156.
$$

The sample scale is therefore `1.7095255431215595%` larger. This is the exact
window-derived result used in the evidence, replacing the forensic approximation.
A negative test proves that sample scaling changes both beta and `cond(X)`.
Future Go code must calculate population standard deviation explicitly; a
Bessel-corrected `stat.StdDev` is not equivalent.

## Condition Consumers

| Consumer | Field | Operator | Threshold | Categorical effect |
|---|---|---|---:|---|
| `EmissionPolicy.emit` | `condition_number` | `<=` | 7.835779770603297 | HIGH only when condition, eigenvalue, and amplification all pass median limits |
| `EmissionPolicy.emit` | `condition_number` | `<=` | 13.040323846425492 | MEDIUM only when all three metrics pass q95 limits; otherwise LOW |

`PriceEmission._build` stores the condition value unchanged. The cockpit receives
the confidence category produced by these comparisons. No other production
condition comparison exists.

## Threshold Risk

The accepted run's nearest median cases are `AAPL-000046` below at
`7.7894081860325` (margin `-0.04637158457079682`) and `AAPL-000098` above at
`7.883378835007342` (margin `+0.04759906440404471`). The nearest q95 case is
`AAPL-000064` below at `10.137631024115974`; no accepted case is above q95.

Observed confidence is joint across condition, eigenvalue, amplification, and
domain state, so a nearby condition does not by itself imply the corresponding
confidence level. Controlled `np.nextafter` fixtures isolate condition and prove
HIGH/MEDIUM immediately across median and MEDIUM/LOW immediately across q95.

## Code Changes

- `dynamics.py`: made existing population semantics explicit with `ddof=0` in
  both full-history reference and active-index production implementations.
- `validate_finding_004.py`: added external finite-run capture, exact replay,
  comparisons, and evidence generation.
- `test_fit_f4_numerical_contract.py`: added eight focused contract tests.

No return type, equation, array order, threshold, retention policy, or production
scheduling changed.

## Golden Corpus

`fit_f4_golden_corpus.jsonl` contains 55 independent cases. Each contains source
identity, all four exact input windows, values, means, population and sample scales,
standardized values, design matrix, ridge matrix, normal matrix, RHS, beta, physical
coefficients, extrema, condition, validity, policy inputs, PriceEmission categories,
and cockpit categories.

Every floating-point value is serialized with `float.hex()`. A case can therefore
be reconstructed exactly with `float.fromhex()` without SDX, Adaptive state, Pricing
history, or another run. Corpus generation monkey-patches only the validation
process; production retains no corpus or audit records.

## Future Go Comparison Contract

The later validator must compare, in order: means, population scales,
standardized values, normal matrix, beta, physical coefficients, condition,
confidence threshold result, and downstream categories. It must stop at the first
divergence. Python replay is bit-exact. A future cross-language numerical tolerance
requires separate evidence and approval; categorical results remain exact.

## Preservation And Exclusions

- Findings 001 analytic projection: preserved.
- Finding 002 active-index scheduling: preserved.
- Finding 003 31-row/zero-default-diagnostic retention: preserved.
- Adaptive, D01, D02, D04, causal-quadratic, IDs, ingress, SDX: unchanged.
- Go, SADE_Go, Volume Pipeline, Decision Engine, Azure: not implemented.

## Scientific Non-Change Attestation

```text
Scientific Mathematics Changed: NO
Standard Deviation: POPULATION
ddof: 0
Normal Equations: PRESERVED
Condition Number: SCIENTIFICALLY DOWNSTREAM-RELEVANT
Go Migration: NOT IMPLEMENTED

QR introduced: NO
SVD introduced: NO
least-squares algorithm substituted: NO
ridge lambda changed: NO
intercept treatment changed: NO
condition-number matrix changed: NO
confidence thresholds changed: NO
```
