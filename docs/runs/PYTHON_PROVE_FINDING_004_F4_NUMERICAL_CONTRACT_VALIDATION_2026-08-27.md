# Python-Prove Finding 004: F4 Numerical Contract Validation

**Date:** August 27, 2026  
**Status:** PASS - GO-MIGRATION NUMERICAL BLOCKER HARDENED  
**Repository:** `C:\Users\chino\SADE`  
**Input:** Current unchanged SDX implementation, AAPL, 100 vectors

## Before Baseline

- Complete package tests: **23 passed, 0 failed**.
- Adaptive: 100 received, 15 initializing, 85 actionable.
- Decisions: 8 BUY, 10 SELL, 67 HOLD.
- Adaptive events: 331 adaptation, 170 feedback.
- Pricing: 85 derivative-ready, 55 F4-ready, 55 emissions, 18 domain exits.
- Confidence: 29 MEDIUM, 26 LOW.
- Price colors: 33 AMBER, 14 GREEN, 8 RED.

Dedicated artifacts are under `output/python_prove/finding_004/before`.

## Production Clarification

Both F4 implementations changed from implicit `values.std(axis=0)` to explicit
`values.std(axis=0, ddof=0)`. The immediate focused active/reference and migration
gate passed: **4 passed**. No numerical field changed.

## Numerical Contract Tests

Eight focused tests freeze:

1. all 55 corpus cases replay bit-exactly;
2. 30-row input window and exact population `ddof=0` scales;
3. design ordering and intercept placement;
4. ridge diagonal, $\lambda=1.0$, and unpenalized intercept;
5. normal-equation matrix and RHS operation order;
6. beta and physical conversion;
7. `cond(design)` and `valid_fit` semantics;
8. condition policy boundaries, downstream categories, and the 31-row retention bound.

Focused result: **8 passed, 0 failed**.

## Population Versus Sample Negative Test

For the actual $N=30$ window:

| Item | Value |
|---|---:|
| Population denominator | 30 |
| Sample denominator | 29 |
| Sample/population ratio | 1.0170952554312156 |
| Sample scale increase | 1.7095255431215595% |

The test uses one accepted corpus window, proves the component scales differ, and
proves the resulting beta and design condition differ. Sample standard deviation
is never used in production.

## Condition Matrix Verification

Corpus replay reconstructs the exact `(30,4)` design matrix and requires:

```text
recorded condition bits == np.linalg.cond(design).hex()
```

The matrix is `design`, not `design.T @ design` and not the ridge-adjusted normal
matrix. Every corpus condition replays exactly.

## Threshold Inventory And Margins

| Threshold | Operator | Nearest below/equal | Nearest above |
|---|---|---|---|
| median `7.835779770603297` | `<=` | index 46: `7.7894081860325` | index 98: `7.883378835007342` |
| q95 `13.040323846425492` | `<=` | index 64: `10.137631024115974` | none in accepted run |

Natural threshold-near representatives: **3**. Controlled `np.nextafter` fixtures
cover immediately below and above both thresholds while companion metrics are held
on the intended policy tier. They prove HIGH to MEDIUM across median and MEDIUM to
LOW across q95. This demonstrates that condition is decision-relevant, not telemetry.

## Golden Corpus Replay

- Schema: `fit_f4_golden_corpus.v1`.
- Cases: **55**, one for every eligible accepted-run F4 fit.
- Float policy: IEEE-754 binary64 hexadecimal strings.
- Inputs are self-contained; replay requires no SDX or prior pipeline state.
- Exact fields: means, scales, beta, physical coefficients, extrema, condition.
- Additional exact matrices: standardized inputs, design, ridge, normal matrix, RHS.
- Sequential PriceEmission categorical replay: PASS.
- Sequential cockpit categorical replay: PASS.

## After Validation

- Complete package tests: **31 passed, 0 failed**.
- Adaptive unchanged-SDX run: PASS, same deterministic rows and summary.
- Integrated Pricing unchanged-SDX run: PASS.
- Pricing observations CSV: byte-identical.
- Pricing observations SHA-256 before and after:
  `4b3b8783108988e71c4bf2cec9b6f8a4c6bf929fb93a4be27706a16ef4c1752a`.
- Pricing migration-equivalence JSON: byte-identical.
- Confidence and color counts: unchanged.

## Prior Finding Regressions

### Finding 001

Focused tests: **2 passed**. Production remains analytic EXPM, production RK45 is
not called, and analytic-versus-reference validation passes.

### Finding 002

Focused tests: **2 passed**. Causal and F4 active-index helpers remain bit-exact to
their full-history references, each active fit is scheduled once, and production
does not perform a full-history refit.

### Finding 003

A fresh 1,000-observation validation completed. Default Adaptive emissions,
initialization records, audits, traces, and row history remain zero. Pricing source
and derivative histories remain at 31. Processing continues with 900 emissions
after observation 100.

## Integrity

```text
SDX MODIFIED: NO
ADAPTIVE MATHEMATICS MODIFIED: NO
CAUSAL_QUADRATIC MODIFIED: NO
FIT_F4 SCIENTIFIC MATHEMATICS MODIFIED: NO
FIT_F4 ddof EXPLICIT: YES
FIT_F4 ddof: 0
NORMAL EQUATIONS MODIFIED: NO
RIDGE LAMBDA MODIFIED: NO
CONDITION NUMBER SEMANTICS MODIFIED: NO
CONFIDENCE THRESHOLDS MODIFIED: NO
FINDING 001 MODIFIED: NO
FINDING 002 SCHEDULING MODIFIED: NO
FINDING 003 RETENTION MODIFIED: NO
GO CODE CREATED: NO
SADE_GO IMPLEMENTED: NO
```

## Artifacts

Machine-readable evidence is under `output/python_prove/finding_004`:

- `fit_f4_numerical_contract.json`
- `fit_f4_golden_corpus.jsonl`
- `corpus_manifest.json`
- `population_vs_sample_std.json`
- `condition_threshold_inventory.json`
- `condition_threshold_margins.json`
- `golden_corpus_replay.json`
- `adaptive_before_after.json`
- `pricing_before_after.json`
- `finding_001_regression.json`
- `finding_002_regression.json`
- `finding_003_regression.json`
- `integrity_summary.json`
- `finding_004_closeout.json`

## Final Status

**RESOLVED - GO-MIGRATION NUMERICAL BLOCKER HARDENED**

The current Python F4 behavior is explicit and independently replayable. It has not
been migrated to Go. Finding 005 was not started.
