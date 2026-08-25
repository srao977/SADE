from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math


class PathDirection(str, Enum):
    UPWARD = "UPWARD"
    DOWNWARD = "DOWNWARD"
    FLAT = "FLAT"


@dataclass(frozen=True)
class ForwardSample:
    tau: float
    level: float
    velocity: float
    uncertainty: float
    strength: float
    persistence: float
    reversal_propensity: float

    def __post_init__(self) -> None:
        for name in ("tau", "level", "velocity", "uncertainty", "strength", "persistence", "reversal_propensity"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.tau <= 0.0:
            raise ValueError("tau must be positive")
        if not -50.0 <= self.velocity <= 50.0:
            raise ValueError("velocity must be in [-50, 50]")
        for name in ("uncertainty", "strength", "persistence", "reversal_propensity"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class ReturnShape:
    model_time: float
    entity_id: str
    source_model_version: str
    current_level: float
    projection_interval: float
    forward_half_life: float
    forward_samples: tuple[ForwardSample, ...]
    terminal_displacement: float
    maximum_absolute_displacement: float
    path_direction: PathDirection
    terminal_decay_factor: float
    strength: float
    coherence: float
    persistence: float
    uncertainty: float
    reversal_propensity: float
    state_support_ratio: float

    def __post_init__(self) -> None:
        for name in (
            "model_time", "current_level", "projection_interval", "forward_half_life",
            "terminal_displacement", "maximum_absolute_displacement", "terminal_decay_factor",
            "strength", "coherence", "persistence", "uncertainty", "reversal_propensity",
            "state_support_ratio",
        ):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if not self.entity_id:
            raise ValueError("entity_id must be non-empty")
        if self.source_model_version != "0.2":
            raise ValueError("source_model_version must be 0.2")
        if not 10.0 <= self.projection_interval <= 600.0:
            raise ValueError("projection_interval must be in [10, 600]")
        if not 15.0 <= self.forward_half_life <= 900.0:
            raise ValueError("forward_half_life must be in [15, 900]")
        if not self.forward_samples:
            raise ValueError("forward_samples must be non-empty")
        if self.maximum_absolute_displacement < 0.0:
            raise ValueError("maximum_absolute_displacement must be nonnegative")
        if not 0.0 < self.terminal_decay_factor < 1.0:
            raise ValueError("terminal_decay_factor must be in (0, 1)")
        for name in ("strength", "coherence", "persistence", "uncertainty", "reversal_propensity"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.state_support_ratio < 0.0:
            raise ValueError("state_support_ratio must be nonnegative")
        taus = [sample.tau for sample in self.forward_samples]
        if any(current <= previous for previous, current in zip(taus, taus[1:])):
            raise ValueError("forward sample tau values must be strictly increasing")
        if taus[-1] != self.projection_interval:
            raise ValueError("terminal sample tau must equal projection_interval")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["forward_samples"] = [asdict(sample) for sample in self.forward_samples]
        payload["path_direction"] = self.path_direction.value
        return payload
