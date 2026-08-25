from __future__ import annotations

import math


def innovation_magnitude(level: float, prev_level: float, prev_velocity: float, dt: float, epsilon: float) -> tuple[float, float]:
    expected = prev_level + prev_velocity * dt
    residual = level - expected
    magnitude = math.sqrt((residual * residual) / max(dt + epsilon, epsilon))
    return residual, magnitude

