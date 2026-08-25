from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class FMOSample:
    tau: float
    level: float
    velocity: float
    uncertainty: float
    strength: float
    persistence: float
    reversal_propensity: float


@dataclass
class DMOOutput:
    model_time: float
    entity_id: str
    model_version: str
    state_level: float
    state_velocity: float
    state_acceleration: float
    state_curvature: float
    strength: float
    coherence: float
    persistence: float
    perturbation_magnitude: float
    perturbation_class: str
    uncertainty: float
    reversal_propensity: float
    state_support_ratio: float
    observation_half_life: float
    forward_half_life: float
    parameter_state: dict[str, float]
    parameter_update_magnitude: dict[str, float]
    data_quality: float
    model_health: str
    dmo_schema_version: str
    fmo_schema_version: str
    config_hash: str
    state_hash: str
    trace_id: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class FMOOutput:
    model_time: float
    entity_id: str
    interval_length: float
    samples: list[FMOSample]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["samples"] = [asdict(row) for row in self.samples]
        return payload

