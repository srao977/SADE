from __future__ import annotations

from sade.d01.v02.config import PersistenceConfig


def update_persistence(prev_persistence: float, velocity: float, prev_velocity: float, acceleration: float, perturbation_class: str, cfg: PersistenceConfig) -> float:
    direction_agreement = 1.0 if velocity * prev_velocity >= 0.0 else 0.0
    accel_penalty = min(1.0, abs(acceleration) / (1.0 + abs(acceleration)))
    pert_penalty = 0.4 if perturbation_class in {"CONTRADICTING", "REVERSING", "STRUCTURAL/UNKNOWN"} else 0.0
    agreement = max(0.0, min(1.0, direction_agreement - accel_penalty * 0.25 - pert_penalty))
    value = (1.0 - cfg.alpha) * prev_persistence + cfg.alpha * agreement
    lo, hi = cfg.bounds
    return max(lo, min(hi, value))

