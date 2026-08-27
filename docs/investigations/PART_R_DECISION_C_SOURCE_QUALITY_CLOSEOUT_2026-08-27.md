# Part R Decision C: Source Quality Executable-Code Closeout

**Date:** August 27, 2026  
**Status:** NOT RESOLVED  
**Repository:** `C:\Users\chino\SADE`  
**Evidence basis:** CURRENT SADE EXECUTABLE `.py` CODE ONLY  
**APTF documentation used as evidence:** NO

## Conclusion

The proposed statement is **false** in current executable code:

> LEGACY `source_quality` / `data_quality` IS NOT PART OF THE CURRENT
> AUTHORITATIVE D01 -> D04 SCIENTIFIC PATH.

`source_quality` is an active D01 scientific input. The current Adaptive ingress
fabricates `data_valid="true"`; the normalizer maps it to `source_quality=1.0`;
and `D01V02Model.step` consumes that value in perturbation classification and
uncertainty. Those results flow through D01 outputs into D02 and D04.

Decision C therefore cannot authorize dropping or not migrating this property
without a separately approved scientific-model change and equivalence analysis.

## Active Dependency

```text
AdaptivePipeline.build_source_row
    data_valid = "true"
        -> SourceRowNormalizer.source_row_to_normalized_observation
           quality_score = 1.0 if data_valid else 0.5
        -> NormalizedObservation.source_quality
        -> D01V02Model.step
           data_quality = clamp(obs.source_quality, 0, 1)
           -> classify_perturbation(source_quality=data_quality)
              quality < 0.5 forces STRUCTURAL/UNKNOWN
           -> compute_uncertainty(data_quality_degradation=1-data_quality)
              coefficient data_quality = 1.0
           -> persistence, reversal, half-life, adaptation, forward output
           -> DMOOutput.data_quality / uncertainty / perturbation fields
        -> D02 build_return_shape
           consumes D01 uncertainty, strength, persistence, reversal, FMO
        -> D04 CapturabilityModelV0_2
           risk_quality uses uncertainty and reversal_propensity
```

`AdaptiveEmitter.process` is the active orchestrator: it calls the normalizer,
then `D01V02Model.step`, `build_return_shape`, and
`CapturabilityModelV0_2.evaluate`. It does not separately read a field named
`source_quality`, but it actively carries the value into D01 through the
normalized observation.

## Current Occurrences

| File / function or class | Field | Access | Active production path | Scientific effect |
|---|---|---|---|---|
| `adaptive_pipeline/pipeline.py::build_source_row` | `data_valid` | write constant `"true"` | YES | YES, through normalizer and D01 |
| `adaptive_pipeline/pipeline.py::AdaptivePipeline.run` | `data_valid` | summary metadata write | YES | NO at this summary site |
| `adaptive_emitter/normalizer.py::SourceRowNormalizer.source_row_to_normalized_observation` | `data_valid` | read/default and map | YES | YES |
| same | `source_quality` | write `1.0` or `0.5` | YES | YES |
| `d01/v02/observations.py::NormalizedObservation` | `source_quality` | contract field/default | YES | YES when consumed by D01 |
| `d01/v02/observations.py::NormalizedObservation.with_defaults` | `source_quality` | read/copy as float | YES | YES |
| `d01/v02/model.py::D01V02Model.step` | `source_quality` | read and clamp | YES | YES |
| same | `source_quality` | pass to `classify_perturbation` | YES | YES |
| same | `data_quality` | derive/read in uncertainty and trace predicates | YES | YES |
| same | `data_quality` | write to `DMOOutput` | YES | YES/provenance output |
| `d01/v02/perturbation.py::classify_perturbation` | `source_quality` | threshold read | YES | YES, can force `STRUCTURAL/UNKNOWN` |
| `d01/v02/uncertainty.py::compute_uncertainty` | `data_quality_degradation` | weighted read | YES | YES, changes uncertainty |
| `d01/v02/config.py::UncertaintyConfig` | `data_quality` | coefficient definition `1.0` | YES | YES |
| `d01/v02/outputs.py::DMOOutput` | `data_quality` | output contract field | YES | Output/provenance; D02 does not read it directly |
| `d01/v02/trace.py::TraceRecord` | `source_quality` | diagnostic contract field | YES when explicit diagnostics enabled | NO additional scientific effect |
| `tests/test_sade_pipeline.py` | `data_valid` | test assertion | NO | NO |

Module header/docstring mentions are descriptive and do not themselves read or
write runtime values.

## D02 And D04

Neither D02 nor D04 directly reads a member named `source_quality` or
`data_quality`. They are nevertheless downstream of its active D01 effects:
D02 copies D01 uncertainty, strength, persistence, and reversal propensity into
`ReturnShape`; D04 uses uncertainty and reversal propensity in risk quality and
capturability. This does not make the property dead at the D01 -> D04 boundary.

## Closeout

```text
LEGACY STATIC QUALITY PROPERTY PART OF CURRENT D01->D04 SCIENCE: YES
DECISION C: NOT RESOLVED
GENERIC SADE_GO RUNTIME BLOCKED: NO
D01->D04 GO MIGRATION BLOCKED BY SOURCE_QUALITY: YES
PRODUCTION CODE MODIFIED: NO
SDX MODIFIED: NO
GO CODE CREATED: NO
```

STOP: removing or omitting this property would change active scientific behavior.