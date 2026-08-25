from __future__ import annotations

from sade.d01.v02.config import AdaptationConfig


def update_parameters(
    params: dict[str, float],
    uncertainty: float,
    strength: float,
    perturbation_multiplier: float,
    cfg: AdaptationConfig,
) -> tuple[dict[str, float], dict[str, float], int]:
    updated = dict(params)
    magnitudes: dict[str, float] = {}
    bound_hits = 0
    for name, current in params.items():
        eta0 = cfg.base_learning_rates.get(name, cfg.min_learning_rate)
        eta = eta0 * max(0.2, 1.0 - uncertainty) * max(0.5, strength) * perturbation_multiplier
        eta = max(cfg.min_learning_rate, min(cfg.max_learning_rate, eta))
        gradient = (strength - uncertainty) * 0.1
        proposal = current + eta * gradient
        lo, hi = cfg.parameter_bounds.get(name, (current - 1.0, current + 1.0))
        clipped = max(lo, min(hi, proposal))
        if clipped != proposal:
            bound_hits += 1
        updated[name] = clipped
        magnitudes[name] = abs(clipped - current)
    return updated, magnitudes, bound_hits

