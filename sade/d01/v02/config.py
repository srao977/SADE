from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json


@dataclass(frozen=True)
class ReferenceConfig:
    alpha: float = 0.05
    min_scale: float = 1e-4


@dataclass(frozen=True)
class KinematicsConfig:
    dt_floor: float = 1e-6
    velocity_bound: float = 50.0
    acceleration_bound: float = 200.0
    curvature_bound: float = 200.0


@dataclass(frozen=True)
class AdaptationConfig:
    base_learning_rates: dict[str, float] = field(default_factory=lambda: {"ref_alpha": 0.005})
    min_learning_rate: float = 1e-4
    max_learning_rate: float = 0.05
    parameter_bounds: dict[str, tuple[float, float]] = field(default_factory=lambda: {"ref_alpha": (0.001, 0.2)})


@dataclass(frozen=True)
class VolumeConfig:
    enabled: bool = True
    reference_alpha: float = 0.05
    influence_bounds: tuple[float, float] = (0.0, 3.0)


@dataclass(frozen=True)
class StrengthConfig:
    coefficients: dict[str, float] = field(
        default_factory=lambda: {
            "bias": -0.25,
            "mass": 0.8,
            "velocity": 0.35,
            "acceleration": 0.2,
            "coherence": 1.0,
            "uncertainty": 1.1,
        }
    )
    bounds: tuple[float, float] = (0.0, 1.0)


@dataclass(frozen=True)
class CoherenceConfig:
    channel_weights: dict[str, float] = field(
        default_factory=lambda: {"displacement": 1.0, "velocity": 1.0, "acceleration": 0.8, "volume": 0.7}
    )


@dataclass(frozen=True)
class PersistenceConfig:
    alpha: float = 0.2
    bounds: tuple[float, float] = (0.0, 1.0)


@dataclass(frozen=True)
class PerturbationConfig:
    thresholds: dict[str, float] = field(
        default_factory=lambda: {"reinforcing": 0.35, "contradicting": 0.55, "reversing": 0.75, "structural": 0.9}
    )
    structural_quality_floor: float = 0.5
    adaptation_multiplier_bounds: tuple[float, float] = (0.8, 1.5)


@dataclass(frozen=True)
class UncertaintyConfig:
    coefficients: dict[str, float] = field(
        default_factory=lambda: {
            "innovation": 1.0,
            "incoherence": 0.8,
            "unknown_perturbation": 0.8,
            "data_quality": 1.0,
            "instability": 0.5,
        }
    )
    bounds: tuple[float, float] = (0.0, 1.0)


@dataclass(frozen=True)
class ReversalConfig:
    coefficients: dict[str, float] = field(
        default_factory=lambda: {
            "oppose": 1.0,
            "contradict": 0.8,
            "low_persistence": 0.7,
            "extreme": 0.8,
            "uncertainty": 0.6,
        }
    )
    bounds: tuple[float, float] = (0.0, 1.0)


@dataclass(frozen=True)
class HalfLifeConfig:
    baseline: float = 120.0
    min: float = 15.0
    max: float = 900.0
    reinforcement_multiplier_bounds: tuple[float, float] = (1.0, 1.35)
    contradiction_multiplier_bounds: tuple[float, float] = (0.5, 1.0)
    perturbation_reset_policy: str = "SHORTEN"


@dataclass(frozen=True)
class ForwardConfig:
    min_interval: float = 10.0
    baseline_interval: float = 60.0
    max_interval: float = 600.0
    sample_count: int = 8
    sampling_exponent: float = 1.8


@dataclass(frozen=True)
class NumericalConfig:
    epsilon: float = 1e-8
    clipping_policy: str = "HARD"
    nonfinite_policy: str = "ERROR"


@dataclass(frozen=True)
class AblationConfig:
    volume_influence: bool = True
    perturbation_adaptation: bool = True
    adaptive_half_life: bool = True
    coherence_influence: bool = True
    reversal_channel: bool = True
    elastic_forward_interval: bool = True


@dataclass(frozen=True)
class D01V02Config:
    model_version: str = "0.2"
    dmo_schema_version: str = "0.2.0"
    fmo_schema_version: str = "0.2.0"
    reference: ReferenceConfig = field(default_factory=ReferenceConfig)
    kinematics: KinematicsConfig = field(default_factory=KinematicsConfig)
    adaptation: AdaptationConfig = field(default_factory=AdaptationConfig)
    volume: VolumeConfig = field(default_factory=VolumeConfig)
    strength: StrengthConfig = field(default_factory=StrengthConfig)
    coherence: CoherenceConfig = field(default_factory=CoherenceConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    perturbation: PerturbationConfig = field(default_factory=PerturbationConfig)
    uncertainty: UncertaintyConfig = field(default_factory=UncertaintyConfig)
    reversal: ReversalConfig = field(default_factory=ReversalConfig)
    half_life: HalfLifeConfig = field(default_factory=HalfLifeConfig)
    forward: ForwardConfig = field(default_factory=ForwardConfig)
    numerical: NumericalConfig = field(default_factory=NumericalConfig)
    ablation: AblationConfig = field(default_factory=AblationConfig)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def sha256(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest().upper()

