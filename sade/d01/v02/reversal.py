from __future__ import annotations

import math

from sade.d01.v02.config import ReversalConfig


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_reversal_propensity(
    velocity: float,
    acceleration: float,
    perturbation_class: str,
    persistence: float,
    level: float,
    uncertainty: float,
    cfg: ReversalConfig,
) -> float:
    oppose = 1.0 if velocity * acceleration < 0.0 else 0.0
    contradict = 1.0 if perturbation_class in {"CONTRADICTING", "REVERSING", "STRUCTURAL/UNKNOWN"} else 0.0
    extreme = min(1.0, abs(level) / 4.0)
    c = cfg.coefficients
    raw = (
        c["oppose"] * oppose
        + c["contradict"] * contradict
        + c["low_persistence"] * (1.0 - persistence)
        + c["extreme"] * extreme
        + c["uncertainty"] * uncertainty
        - 1.2
    )
    val = _sigmoid(raw)
    lo, hi = cfg.bounds
    return max(lo, min(hi, val))

