# Python-Proove Before Plan

**Date:** August 27, 2026\
**Status:** REFERENCE PLAN --- PRE-SADe_Go SCIENTIFIC BASELINE AND
CORRECTION SEQUENCE\
**Document:** `Python-Proove_Before_plan.md`

## Purpose

This document defines the controlled pre-SADe_Go work required to
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

Four pre-Go matters are then handled under controlled validation:

1.  Establish the ID-equivalence contract.
2.  Capture a real ingress/receive timestamp at the SADE boundary.
3.  Remove O(n²) Pricing recomputation while preserving scientific
    results.
4.  Bound or externalize unbounded in-memory collections while
    preserving scientific results.

The O(n²) and bounded-state corrections must be performed separately.

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

## Fix A --- ID Equivalence Contract

For this Python correction phase:

> **Where the underlying scientific observation or emission is
> unchanged, the corrected Python implementation must preserve
> `observation_id` and `emission_id` byte-for-byte.**

This is a migration/equivalence invariant, not necessarily the permanent
SADE_Go identity design.

## Fix B --- Genuine SADE Ingress Timestamp

Do not modify SDX to create latency semantics. Capture real arrival time
at the SADE ingestion boundary:

``` text
SDX MarketVector
    source_timestamp
        │
        │ gRPC
        ▼
SADE receives vector
        │
        ├── source_timestamp     ← unchanged from SDX
        └── receive/ingress_time ← captured HERE
```

The ingress timestamp is operational metadata and must not affect
scientific calculations.

Maintain the distinction between inherent **scientific/model latency**
and measurable **computational/transport latency**.

## Fix C --- Eliminate O(n²) Pricing Recomputation

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

Treat `fit_f4` as high-sensitivity. Small numerical drift can cross
thresholds and create categorical differences.

If an unexpected scientific mismatch occurs: **STOP, identify the first
differing intermediate value, correct the implementation, and rerun
equivalence.**

Do not proceed to Fix D until Fix C passes.

## Fix D --- Bound Unbounded State Accumulation

After Fix C passes independently, address collections that grow
indefinitely.

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

## RK45 During This Plan

Do not replace RK45.

The finding that the current ODE is an affine, constant-coefficient,
non-stiff three-dimensional system and that `expm(A)` can later provide
an independent analytic validation oracle is reserved for the Go
migration phase.

## `fit_f4` During This Plan

Do not translate `fit_f4` to Go.

Preserve current standardization semantics,
population-standard-deviation behavior, coefficient construction,
condition-number behavior, operation ordering where output-sensitive,
and threshold-driving outputs.

## SDX Role During This Plan

Classify current SDX as:

> **Current deterministic Go input/streaming implementation and
> validation source --- not yet the final SADE_Go ingress
> architecture.**

Future work may change it for asynchronous inputs, multiple simultaneous
sources, generalized source adapters, `IO_Vector` construction,
near-real-time ingestion, Azure transport, partitioning, and
backpressure.

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
