# Python-Prove Before Plan

**Date:** August 27, 2026\
**Status:** REFERENCE PLAN --- PRE-SADE_Go SCIENTIFIC BASELINE AND
CORRECTION SEQUENCE\
**Document:** `Python-Prove_Before_plan.md`

## Purpose

This document defines the controlled pre-SADE_Go work required to
establish an authoritative **Python Before** scientific baseline and
then correct the known scale/runtime issues in the current Python SADE
implementation without conflating those corrections with the later
Python-to-Go migration.

> **First prove exactly what the current Python SADE does. Then make
> each pre-Go correction independently and prove that scientific
> behavior remains unchanged. Only after that should SADE_Go migration
> begin.**

The existing SDX implementation is deliberately left unchanged during
this phase and used as the deterministic input/streaming source.

## Scope

This plan covers:

-   capture of the authoritative current Python scientific behavior;
-   the equivalence contract for `observation_id` and `emission_id`;
-   introduction of a genuine SADE ingress/receive timestamp;
-   removal of unnecessary O(n²) Pricing Pipeline historical
    recomputation;
-   removal or bounding of unbounded in-memory collections;
-   scientific equivalence validation after each individual correction;
-   creation of a new frozen Python baseline for later SADE_Go
    migration.

This plan does **not** authorize SADE_Go implementation.

## Executive Summary

SDX should remain unchanged during this work. It is sufficient as a
deterministic stimulus/input source, while its eventual architecture may
need substantial revision for asynchronous, multi-source, near-real-time
operation.

Before Go migration, SADE needs a detailed Python reference corpus
containing important intermediate scientific states and numerical
results, not merely final decisions.

The repository investigation identified the following concrete findings
that govern this plan:

1.  `solve_cover` integrates an **affine, constant-coefficient,
    non-stiff 3-dimensional ODE**. `numerical.py` already computes
    `expm(A)`, which provides an independent analytic validation oracle
    for a future Go integrator. This is **not** authorization to replace
    RK45 in the current Python path.
2.  `causal_quadratic` and `fit_f4` refit the entire history on every
    observation while `pipeline.py` reads only one active index. This is
    O(n²) cumulative work and is mathematically free to correct without
    changing the model.
3.  Eight identified collections grow without bound. The 100-observation
    run already produced **331 adaptation-audit entries**. This is a
    separate scale blocker and must be corrected independently of the
    O(n²) change.
4.  `fit_f4` is the highest-risk later Go migration point, not RK45. It
    forms normal equations, thereby squaring the condition number, and
    its `cond` result feeds hard-coded confidence thresholds. Small
    continuous numerical drift can therefore create discrete label
    flips. In addition, `np.std` uses population standard deviation
    (`ddof=0`), whereas Gonum `stat.StdDev` applies Bessel correction; a
    naïve translation would introduce approximately **1.74% error** in
    every scale and coefficient.
5.  Runtime latency is currently **unmeasurable in principle** because
    `normalizer.py` fabricates `receive_time = event_time` and no true
    ingress timestamp exists.
6.  The SDX Go implementation is currently untracked in Git. This is a
    known provenance risk, but by explicit decision it is **not
    corrected during Python-Prove Before**. SDX remains unchanged and is
    used as the deterministic test/input source because its eventual
    asynchronous, multi-source real-time architecture may differ
    substantially.
7.  Whether `observation_id` and `emission_id` must remain
    byte-identical is a human decision. It must be settled before byte
    identity is made an acceptance criterion, because a future Go
    implementation may otherwise need to reproduce CPython float
    representation.

The O(n²) correction and the unbounded-collection correction must be
performed separately and validated against the frozen Python-before
baseline so that scientific drift can never be attributed to two causes
at once.

## Final Objective

Produce a scientifically authoritative and operationally cleaner
**frozen Python SADE baseline** that becomes the oracle for subsequent
component-by-component migration into SADE_Go.

The later objective remains a scaled, predominantly Go runtime capable
of processing thousands of independent `IO_Vector` channels concurrently
in near real-time, ultimately on Azure.

## Current Reference Flow

``` text
CURRENT SDX
leave unchanged
use as deterministic input source
        │
        ▼
CURRENT PYTHON SADE
        │
        ├── FIRST: capture "PYTHON BEFORE"
        │   detailed frozen output/equivalence corpus
        │
        ├── FIX A
        │   ID migration/equivalence decision
        │
        ├── FIX B
        │   genuine ingress/receive timestamp
        │
        ├── FIX C
        │   eliminate O(n²) Pricing recomputation
        │
        ├── FIX D
        │   eliminate unbounded state accumulation
        │
        ▼
CORRECTED PYTHON SADE
        │
        ▼
compare against PYTHON BEFORE
        │
        ├── scientific values
        ├── state evolution
        ├── classifications
        ├── IDs as agreed
        └── final outputs
        │
        ▼
NEW FROZEN PYTHON SCIENTIFIC BASELINE
        │
        ▼
SADE_Go work begins
```

## Governing Rules

### SDX remains unchanged

During this plan, SDX is a deterministic input source. Do not redesign
its CSV reader, streaming model, source architecture, or Azure
integration. Future SADE_Go design will determine which SDX components
survive or change.

### Do not combine Python corrections with Go migration

No scientific Python-to-Go translation occurs during this phase.

### One correction at a time

``` text
Python Before
     ↓
Fix A / contract decision
     ↓
validation
     ↓
Fix B
     ↓
validation
     ↓
Fix C — O(n²) only
     ↓
scientific equivalence PASS
     ↓
checkpoint
     ↓
Fix D — bounded state only
     ↓
scientific equivalence PASS
     ↓
new frozen Python baseline
```

### Scientific mathematics must not be redesigned

This phase may change computational scheduling, state retention,
instrumentation, and runtime mechanics where explicitly authorized. It
must not simplify, replace, or reinterpret validated mathematics.

## Phase 0 --- Capture the Authoritative Python Before

Before modifying SADE, execute the current Python path using unchanged
SDX and capture a detailed scientific equivalence corpus.

The corpus must allow us to answer:

> For the same ordered input observations, did the corrected
> implementation produce the same scientific state and outputs as the
> original Python implementation?

### Adaptive-path evidence

Capture where applicable:

-   normalized inputs and observation identity;
-   initialization status;
-   D01 inputs, state, parameters, dynamic outputs, adaptation and
    feedback state;
-   D02 Return Shape outputs;
-   D04 Trading Envelope/capturability outputs;
-   AdaptiveEmitter inputs and outputs;
-   state transitions;
-   audit/trace values required for equivalence.

### Pricing-path evidence

Capture at minimum:

-   required source price history;
-   `p`, `p1`, `p2`, `jp`;
-   derivative state;
-   F4 inputs/window;
-   F4 means and population scales;
-   standardized values;
-   beta/fitted coefficients and physical coefficients;
-   condition number;
-   RK45 inputs, projected/terminal state and success/failure;
-   `projected_p`, `projected_p1`, `projected_p2`;
-   eigenvalue/stability results;
-   `max_real_eigenvalue`;
-   perturbation amplification;
-   PriceEngine numerical input;
-   PriceEmission;
-   cockpit/interpreted state where applicable;
-   final Pricing output.

The corpus should be deterministic, ordered, machine-comparable,
sufficiently detailed to localize mismatches, immutable once accepted,
and accompanied by integrity hashes for authoritative artifacts.

## Fix A --- Decide the ID Equivalence Contract

The investigation leaves one human decision open: whether
`observation_id` and `emission_id` must remain byte-identical during the
Python correction phase and later Python-to-Go migration.

Do **not** silently impose byte identity before this decision is made.

The decision must explicitly state whether equivalence means:

-   byte-identical `observation_id` and `emission_id`; or
-   scientifically equivalent identity under a separately defined
    canonical representation.

This matters for the later Go migration because byte identity may
require Go to reproduce CPython float representation.

Once the human decision is recorded, the chosen rule becomes the
acceptance criterion for all subsequent Python-Prove comparisons.

## Fix B --- Make Runtime Latency Measurable

The repository-specific defect is:

> `normalizer.py` fabricates `receive_time = event_time`, and there is
> no genuine ingress timestamp anywhere in the current path.

Therefore runtime latency is not merely unreported; it is currently
**unmeasurable in principle**.

Do not modify SDX to solve this during Python-Prove Before. SDX remains
the unchanged deterministic input source.

Introduce a genuine arrival/ingress timestamp at the SADE ingestion
boundary while preserving the source/event timestamp:

``` text
SDX MarketVector
    source/event timestamp
        │
        │ gRPC
        ▼
SADE ingress
        │
        ├── source/event timestamp  ← preserved
        └── real ingress timestamp  ← captured at actual arrival
```

The new timestamp is operational metadata. It must not alter scientific
calculations or scientific state.

Maintain the distinction between inherent **scientific/model latency**
and measurable **computational/transport latency**.

## Fix C --- Eliminate O(n²) Pricing Recomputation

The repository finding is specific: `causal_quadratic` and `fit_f4`
refit the entire history on every observation while `pipeline.py` reads
only one active index. Cumulatively this is O(n²). Because the required
calculation depends on the relevant trailing window, this is
mathematically free to correct without changing the model.

The correction changes computation scheduling, not mathematics:

``` text
CURRENT

new observation
      ↓
recompute old windows 0...N
      ↓
take result N-1
      ↓
discard repeated historical work


TARGET

new observation
      ↓
retain required trailing state
      ↓
compute exactly the newly required
derivative/F4 result
      ↓
emit
```

Do not validate only final classifications. Compare:

-   `p`, `p1`, `p2`, `jp`;
-   F4 means, population scales, standardized values;
-   beta/fitted and physical coefficients;
-   `condition_number`;
-   `projected_p`, `projected_p1`, `projected_p2`;
-   `max_real_eigenvalue`;
-   perturbation amplification;
-   PriceEmission fields;
-   cockpit/interpreted fields;
-   final Pricing outputs.

Treat `fit_f4` as the **highest-risk numerical component for later Go
migration**. It forms normal equations, which square the condition
number, and its `cond` output feeds hard-coded confidence thresholds.
Continuous numerical drift can therefore produce discrete label flips.

Preserve the existing `np.std` population-standard-deviation semantics
(`ddof=0`). Do not substitute sample-standard-deviation semantics. The
investigation identified that a naïve use of Gonum `stat.StdDev` in the
later migration would apply Bessel correction and introduce
approximately **1.74% error** in every scale and coefficient.

If an unexpected scientific mismatch occurs: **STOP, identify the first
differing intermediate value, correct the implementation, and rerun
equivalence.**

Do not proceed to Fix D until Fix C passes.

## Fix D --- Bound Unbounded State Accumulation

After Fix C passes independently, address the repository finding that
**eight collections grow without bound**. The 100-observation run
already produced **331 adaptation-audit entries**.

This is an independent thousands-of-channel scale blocker and must not
be combined with the O(n²) correction.

First classify each collection:

``` text
SCIENTIFIC STATE — REQUIRED
RUNTIME STATE — REQUIRED
BOUNDED ROLLING HISTORY — REQUIRED
DIAGNOSTIC/AUDIT HISTORY — NOT REQUIRED IN HOT MEMORY
OUTPUT HISTORY — SHOULD BE EXTERNALIZED
UNKNOWN — INVESTIGATE BEFORE CHANGE
```

Potential categories include emissions, initialization records,
adaptation and feedback audits, D01 traces, pipeline row histories,
Pricing histories, and diagnostic/output accumulators.

Do not simply truncate collections globally.

Target concept:

``` text
IO_Vector Channel 1 ──► bounded state 1 ──► SADE ──► output 1
IO_Vector Channel 2 ──► bounded state 2 ──► SADE ──► output 2
IO_Vector Channel 3 ──► bounded state 3 ──► SADE ──► output 3
 ...
IO_Vector Channel N ──► bounded state N ──► SADE ──► output N
```

This prepares for SADE_Go but does not authorize multi-channel Go
implementation.

## Scientific Equivalence Gates

Each correction must pass all applicable gates:

1.  **Input equivalence** --- same ordered source observations.
2.  **Intermediate equivalence** --- authoritative scientific
    intermediate values match under agreed exact/tolerance rules.
3.  **State-transition equivalence** --- scientific state evolves
    identically.
4.  **Classification equivalence** --- discrete states and outputs match
    exactly.
5.  **ID equivalence** --- IDs satisfy the Fix A contract.
6.  **Final output equivalence** --- Adaptive and Pricing outputs match.
7.  **Determinism** --- repeated identical input produces identical
    accepted output.

## Numerical Comparison Policy

Do not use one global floating-point tolerance without justification.
Classify each field as exact equality, field-specific absolute
tolerance, field-specific relative tolerance, or structured array/matrix
comparison.

Threshold-driving numerical fields require special scrutiny.

## RK45 / `solve_cover` During This Plan

Do not replace RK45.

The repository finding is that `solve_cover` integrates an **affine,
constant-coefficient, non-stiff 3-dimensional ODE**, while
`numerical.py` already computes `expm(A)`, which is its analytic
solution.

This is useful because a future Go RK45 implementation will face a
favorable validation problem and can be checked against both SciPy RK45
and the independent `expm(A)` oracle.

It is **not** a licence to replace or simplify the current RK45
mathematics during Python-Prove Before.

## `fit_f4` During This Plan

Do not translate `fit_f4` to Go during this plan.

`fit_f4` is the investigation's **highest-risk later migration point**.
It forms normal equations and therefore squares the condition number.
Its `cond` output participates in hard-coded confidence thresholds, so
small floating-point drift can cause discrete classification changes.

Preserve current behavior exactly, including:

-   `np.std` population semantics (`ddof=0`);
-   standardization behavior;
-   coefficient construction;
-   normal-equation behavior;
-   condition-number behavior;
-   operation ordering where output-sensitive;
-   all threshold-driving outputs.

For later Go migration, do not assume Gonum `stat.StdDev` is equivalent:
its Bessel correction would change the scale and coefficients by the
approximately **1.74%** identified in the investigation.

## SDX Role During This Plan

Classify current SDX as:

> **Current deterministic Go input/streaming implementation and
> validation source --- not yet the final SADE_Go ingress
> architecture.**

The investigation also found that the entire current SDX Go
implementation is untracked in Git. Record this as a **known provenance
risk**, but do not fix or otherwise modify SDX during Python-Prove
Before.

Future work may change SDX substantially for asynchronous inputs,
multiple simultaneous real-time sources, generalized source adapters,
`IO_Vector` construction, near-real-time ingestion, Azure transport,
partitioning, and backpressure. This is why the current SDX
implementation is retained as-is for deterministic validation rather
than prematurely treated as the final ingress architecture.

## Explicit Exclusions

Do not:

-   start SADE_Go implementation;
-   translate scientific modules to Go;
-   redesign SDX;
-   introduce Python worker pools;
-   establish permanent Adaptive/Pricing wrapper-pool architecture;
-   introduce Azure runtime infrastructure;
-   develop the Volume Pipeline;
-   implement the Go Decision Engine;
-   implement paper-order execution;
-   change scientific equations;
-   combine Fix C and Fix D in one implementation step.

## Required Checkpoints

**Checkpoint 0 --- Python Before Frozen**\
Required before any correction.

**Checkpoint A --- ID Contract Accepted**\
Required before IDs are used as equivalence evidence.

**Checkpoint B --- Ingress Timestamp Added**\
Must prove no scientific effect.

**Checkpoint C --- O(n²) Correction Accepted**\
Must independently pass scientific equivalence.

**Checkpoint D --- Bounded-State Correction Accepted**\
Must independently pass scientific equivalence.

**Final Checkpoint --- Corrected Python Baseline Frozen**\
Becomes the scientific migration oracle for SADE_Go.

## Final Deliverable

``` text
UNCHANGED SDX
      +
CORRECTED, VALIDATED PYTHON SADE
      +
AUTHORITATIVE PYTHON-BEFORE CORPUS
      +
CORRECTION-BY-CORRECTION EQUIVALENCE EVIDENCE
      +
NEW FROZEN PYTHON SCIENTIFIC BASELINE
```

Only then should the first SADE_Go implementation/refactoring phase
begin.

## Next Phase

After this plan is completed and accepted, SADE_Go migration can proceed
component-by-component using the frozen corrected Python implementation
as the scientific oracle.

**SADE_Go implementation is explicitly not authorized by this plan.**
