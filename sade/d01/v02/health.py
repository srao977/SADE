from __future__ import annotations

import math

from sade.d01.v02.state import RuntimeState


def evaluate_health(state: RuntimeState) -> str:
    values = [
        state.state_vector.level,
        state.state_vector.velocity,
        state.state_vector.acceleration,
        state.state_vector.curvature,
        state.state_vector.strength,
        state.state_vector.persistence,
        state.state_vector.uncertainty,
        state.state_vector.reversal_propensity,
        state.half_life_state.observation_half_life,
        state.half_life_state.forward_half_life,
    ]
    if any((not math.isfinite(v)) for v in values):
        state.nonfinite_count += 1
        return "INVALID"
    if state.data_gap_count > 0:
        return "DEGRADED_DATA"
    if state.clipping_count > 0 or state.parameter_bound_hits > 0:
        return "DEGRADED_NUMERICAL"
    if state.state_vector.perturbation_magnitude > 0.7:
        return "PERTURBED"
    return "HEALTHY"

