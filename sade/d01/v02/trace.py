from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TraceRecord:
    trace_id: str
    model_time: float
    sequence: int
    innovation_magnitude: float
    perturbation_materiality_floor: float
    perturbation_detected: bool
    prior_velocity: float
    current_velocity: float
    velocity_change: float
    source_quality: float
    perturbation_class: str
    perturbation_magnitude: float
    strength: float
    uncertainty: float
    persistence: float
    reversal_propensity: float
    observation_half_life: float
    forward_half_life: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

