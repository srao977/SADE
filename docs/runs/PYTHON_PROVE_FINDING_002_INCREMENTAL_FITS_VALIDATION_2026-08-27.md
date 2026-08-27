# Python-Prove Finding 002: Incremental Fits Validation

Date: August 27, 2026

## Result

Status: **PASS**

The O(n²) repeated derivative and F4 fitting was removed from the live Pricing
path. Exact helper/reference comparisons, fit-call instrumentation, package tests,
unchanged-SDX runs, and the Finding 001 regression gate all passed.

## Frozen Baseline

- Package tests: `17 passed`
- SDX-backed Adaptive: 100 received, 85 actionable, 15 initializing
- Integrated Pricing: 100 received, 85 derivative-ready, 55 F4-ready,
  55 emissions, 18 domain exits
- SDX revision: `1b685678e5dbbcb4ed93c2aaf9259f42353c3a3e`
- The existing SDX worktree was not modified.

Baseline artifacts are under `output/python_prove/finding_002/before`.

## Exactness Gates

The active-index derivative helper was compared at every index of a deterministic
100-row irregular-time fixture. Every `p1` and `p2` IEEE-754 byte sequence and the
aggregate failure count matched the full-history reference.

The active-index F4 helper was compared at every index. Availability and every
value in `standardized`, `physical`, `means`, `scales`, `minimum`, `maximum`, and
`condition` matched the full-history reference byte-for-byte.

The before/after integrated Pricing observation files are byte-identical:

`4B3B8783108988E71C4BF2CEC9B6F8A4C6BF929FB93A4BE27706A16EF4C1752A`

The before/after migration metadata files are also byte-identical:

`FA3B2A6F5EBC917CF0C626D47235E0B0E4EE6A396A8193BF1BC3B1724992A424`

All 100 Adaptive rows matched exactly across every scientific and deterministic
field. `observation_id` matched exactly. Timing-derived `emission_id` was validated
per run as non-empty, unique, and count-complete under the corrected Finding 001
rule; its bytes were not compared across independent executions.

All deterministic fields in the three Adaptive/Pricing summaries matched after
excluding only `generated_at_utc` and `output_dir` operational metadata.

## Work Count

NumPy operations were instrumented while replaying the old full-history schedule
and the new live pipeline over the identical 100 SDX-derived records.

| Operation | Old schedule | New schedule | Reduction |
|---|---:|---:|---:|
| Quadratic `lstsq` fits | 3,741 | 85 | 97.7% |
| F4 ridge `solve` calls | 1,540 | 55 | 96.4% |

The production scheduling test observed derivative helper indices `0..98` and F4
helper indices `44..98`, each strictly once. Warmup helper calls do not execute a
least-squares fit until sufficient derivative history exists.

## Regression Gates

- Focused Pricing tests: `8 passed`
- Complete package tests: `19 passed, 0 failed`
- VS Code diagnostics on all touched files: no errors
- Adaptive after-run: **PASS**, unchanged scientific output
- Integrated Pricing after-run: **PASS**, byte-identical observation output
- Finding 001 analytic versus RK45 reference: **PASS**
- Finding 001 solves compared: 55
- Finding 001 trajectory points compared: 605
- Production RK45 execution guard: **PASS**

After artifacts and machine-readable comparisons are under
`output/python_prove/finding_002/after` and
`output/python_prove/finding_002/comparisons`.

## Scope Declarations

- Scientific equations changed: **NO**
- Derivative mathematics changed: **NO**
- F4 mathematics changed: **NO**
- Projection implementation changed: **NO**
- PriceEngine or cockpit behavior changed: **NO**
- Existing history retention changed: **NO**
- Unbounded-state fix included: **NO**
- SDX modified: **NO**
- Go code created: **NO**

Finding 002 is resolved.