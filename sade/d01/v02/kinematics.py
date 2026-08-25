from __future__ import annotations

from sade.d01.v02.config import KinematicsConfig


def _clip(value: float, bound: float) -> tuple[float, bool]:
    if value > bound:
        return bound, True
    if value < -bound:
        return -bound, True
    return value, False


def compute_kinematics(
    price: float,
    reference: float,
    scale: float,
    prev_level: float,
    prev_velocity: float,
    dt: float,
    cfg: KinematicsConfig,
    epsilon: float,
) -> tuple[float, float, float, float, int]:
    dt_eff = max(cfg.dt_floor, dt)
    level = (price - reference) / max(scale, epsilon)
    velocity = (level - prev_level) / (dt_eff + epsilon)
    velocity, v_clip = _clip(velocity, cfg.velocity_bound)
    acceleration = (velocity - prev_velocity) / (dt_eff + epsilon)
    acceleration, a_clip = _clip(acceleration, cfg.acceleration_bound)
    curvature = acceleration / ((1.0 + velocity * velocity) ** 1.5)
    curvature, c_clip = _clip(curvature, cfg.curvature_bound)
    return level, velocity, acceleration, curvature, int(v_clip) + int(a_clip) + int(c_clip)

