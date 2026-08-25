from __future__ import annotations

from sade.d01.v02.config import HalfLifeConfig


def adapt_half_life(current: float, persistence: float, strength: float, uncertainty: float, perturbation_class: str, cfg: HalfLifeConfig) -> float:
    reinforce_gain = 1.0 + (persistence * strength * 0.2)
    contradict_loss = 1.0 - (uncertainty * 0.35)
    rlo, rhi = cfg.reinforcement_multiplier_bounds
    clo, chi = cfg.contradiction_multiplier_bounds
    reinforce_gain = max(rlo, min(rhi, reinforce_gain))
    contradict_loss = max(clo, min(chi, contradict_loss))
    updated = current * reinforce_gain * contradict_loss
    if perturbation_class in {"CONTRADICTING", "REVERSING", "STRUCTURAL/UNKNOWN"} and cfg.perturbation_reset_policy == "SHORTEN":
        updated *= 0.75
    return max(cfg.min, min(cfg.max, updated))

