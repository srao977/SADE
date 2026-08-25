from __future__ import annotations

import math

from sade.d01.v02.outputs import DMOOutput, FMOOutput
from sade.d02.v02.models import ForwardSample, PathDirection, ReturnShape


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _require_bounded(name: str, value: float, lower: float, upper: float) -> None:
    _require_finite(name, value)
    if not lower <= value <= upper:
        raise ValueError(f"{name} must be in [{lower}, {upper}]")


def _validate_input(dmo: DMOOutput, fmo: FMOOutput) -> None:
    if not isinstance(dmo, DMOOutput):
        raise TypeError("dmo must be a DMOOutput")
    if not isinstance(fmo, FMOOutput):
        raise TypeError("fmo must be an FMOOutput")
    if dmo.model_time != fmo.model_time:
        raise ValueError("DMO and FMO model_time must match")
    if dmo.entity_id != fmo.entity_id:
        raise ValueError("DMO and FMO entity_id must match")
    if dmo.model_version != "0.2":
        raise ValueError("D02 v0.2 requires D01 model_version 0.2")
    if not dmo.entity_id:
        raise ValueError("entity_id must be non-empty")

    _require_finite("model_time", dmo.model_time)
    _require_finite("state_level", dmo.state_level)
    _require_bounded("forward_interval", fmo.interval_length, 10.0, 600.0)
    _require_bounded("forward_half_life", dmo.forward_half_life, 15.0, 900.0)
    for name in ("strength", "coherence", "persistence", "uncertainty", "reversal_propensity"):
        _require_bounded(name, getattr(dmo, name), 0.0, 1.0)
    _require_finite("state_support_ratio", dmo.state_support_ratio)
    if dmo.state_support_ratio < 0.0:
        raise ValueError("state_support_ratio must be nonnegative")
    if not fmo.samples:
        raise ValueError("forward_samples must be non-empty")

    previous_tau = 0.0
    for index, sample in enumerate(fmo.samples):
        prefix = f"forward_samples[{index}]"
        _require_finite(f"{prefix}.tau", sample.tau)
        if sample.tau <= previous_tau:
            raise ValueError("forward sample tau values must be strictly increasing")
        if sample.tau > fmo.interval_length:
            raise ValueError("forward sample tau cannot exceed projection interval")
        previous_tau = sample.tau
        _require_finite(f"{prefix}.level", sample.level)
        _require_bounded(f"{prefix}.velocity", sample.velocity, -50.0, 50.0)
        for name in ("uncertainty", "strength", "persistence", "reversal_propensity"):
            _require_bounded(f"{prefix}.{name}", getattr(sample, name), 0.0, 1.0)
    if fmo.samples[-1].tau != fmo.interval_length:
        raise ValueError("terminal forward sample tau must equal projection interval")


def build_return_shape(dmo: DMOOutput, fmo: FMOOutput) -> ReturnShape:
    _validate_input(dmo, fmo)

    samples = tuple(
        ForwardSample(
            tau=sample.tau,
            level=sample.level,
            velocity=sample.velocity,
            uncertainty=sample.uncertainty,
            strength=sample.strength,
            persistence=sample.persistence,
            reversal_propensity=sample.reversal_propensity,
        )
        for sample in fmo.samples
    )
    terminal_displacement = samples[-1].level - dmo.state_level
    maximum_absolute_displacement = max(
        abs(sample.level - dmo.state_level) for sample in samples
    )
    if terminal_displacement > 0.0:
        path_direction = PathDirection.UPWARD
    elif terminal_displacement < 0.0:
        path_direction = PathDirection.DOWNWARD
    else:
        path_direction = PathDirection.FLAT
    terminal_decay_factor = 2.0 ** (-fmo.interval_length / dmo.forward_half_life)

    return ReturnShape(
        model_time=dmo.model_time,
        entity_id=dmo.entity_id,
        source_model_version=dmo.model_version,
        current_level=dmo.state_level,
        projection_interval=fmo.interval_length,
        forward_half_life=dmo.forward_half_life,
        forward_samples=samples,
        terminal_displacement=terminal_displacement,
        maximum_absolute_displacement=maximum_absolute_displacement,
        path_direction=path_direction,
        terminal_decay_factor=terminal_decay_factor,
        strength=dmo.strength,
        coherence=dmo.coherence,
        persistence=dmo.persistence,
        uncertainty=dmo.uncertainty,
        reversal_propensity=dmo.reversal_propensity,
        state_support_ratio=dmo.state_support_ratio,
    )
