from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StateVector:
    level: float = 0.0
    velocity: float = 0.0
    acceleration: float = 0.0
    curvature: float = 0.0
    strength: float = 0.0
    persistence: float = 0.0
    perturbation_magnitude: float = 0.0
    uncertainty: float = 0.15
    reversal_propensity: float = 0.1
    decay_relevance: float = 1.0


@dataclass
class HalfLifeState:
    observation_half_life: float
    forward_half_life: float


@dataclass
class RuntimeState:
    entity_id: str
    model_time: float = 0.0
    sequence: int = 0
    adaptive_reference: float = 0.0
    adaptive_scale: float = 1.0
    volume_reference: float = 1.0
    prev_level: float = 0.0
    prev_velocity: float = 0.0
    last_event_time: float | None = None
    last_observation: object | None = None
    parameter_state: dict[str, float] = field(default_factory=lambda: {"ref_alpha": 0.05})
    parameter_update_magnitude: dict[str, float] = field(default_factory=dict)
    state_vector: StateVector = field(default_factory=StateVector)
    half_life_state: HalfLifeState = field(default_factory=lambda: HalfLifeState(120.0, 120.0))
    clipping_count: int = 0
    nonfinite_count: int = 0
    parameter_bound_hits: int = 0
    innovation_extreme_count: int = 0
    data_gap_count: int = 0

