# Python-Prove Finding 002: Incremental Derivative and F4 Fits

Date: August 27, 2026

Repository: `C:\Users\chino\SADE`

## Finding

The live Pricing pipeline called the full-history `causal_quadratic` and `fit_f4`
functions for every newly received observation, but consumed only
`active_index = current_index - 1`.

For a stream of length $N$, the repeated causal quadratic loop performed

$$
\sum_{k=W}^{N}(k-W+1) = O(N^2)
$$

fits. F4 had the same repeated-history pattern after its warmup period.

## Implementation

- Added `causal_quadratic_at_index`, which executes the unchanged quadratic
  design construction and `np.linalg.lstsq` operation for one requested index.
- Added `fit_f4_at_index`, which executes the unchanged standardization, ridge
  normal equation, physical coefficient conversion, envelope bounds, and
  condition calculation for one requested index.
- Retained `causal_quadratic` and `fit_f4` unchanged as full-history references
  for migration and equivalence validation.
- Added retained `p1`, `p2`, and `jp` histories to `PricingPipeline`.
- Preserved the one-observation lag. A derivative is computed only when its row
  becomes the active index, and an F4 model is fitted at most once for that row.
- Materialized a compatibility fit container only for the active row so the
  projection and numerical assembly contracts remain unchanged.

## Scope Control

Scientific mathematics changed: **NO**

Computational scheduling changed: **YES**

Historical derivative/F4 recomputation removed: **YES**

Finding 001 analytic projection changed: **NO**

ODE equations changed: **NO**

Adaptive science changed: **NO**

Active-index rule changed: **NO**

Timestamp normalization or cadence logic added: **NO**

Unbounded-state fix included: **NO**. Existing histories are deliberately retained;
that concern remains a separate finding.

SDX modified: **NO**

Go code created: **NO**

## Files

- `sade/pricing_pipeline/derivatives.py`
- `sade/pricing_pipeline/dynamics.py`
- `sade/pricing_pipeline/pipeline.py`
- `tests/test_pricing_pipeline.py`

The complete validation record is in
`docs/runs/PYTHON_PROVE_FINDING_002_INCREMENTAL_FITS_VALIDATION_2026-08-27.md`.