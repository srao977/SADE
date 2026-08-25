from __future__ import annotations

from sade.d01.v02.config import ForwardConfig


def compute_forward_interval(
    baseline: float,
    persistence: float,
    strength: float,
    uncertainty: float,
    perturbation_magnitude: float,
    cfg: ForwardConfig,
) -> float:
    length = baseline * (0.7 + 0.6 * persistence) * (0.7 + 0.6 * strength) * (1.1 - 0.8 * uncertainty) * (1.0 - 0.35 * perturbation_magnitude)
    return max(cfg.min_interval, min(cfg.max_interval, length))


def forward_samples(length: float, sample_count: int, exponent: float) -> list[float]:
    points: list[float] = []
    if sample_count <= 0:
        return points
    for idx in range(1, sample_count + 1):
        tau = length * ((idx / sample_count) ** exponent)
        points.append(tau)
    return points


def propagate_level(level: float, velocity: float, acceleration: float, tau: float) -> float:
    return level + velocity * tau + 0.5 * acceleration * tau * tau

