from __future__ import annotations

import math

from sade.d01.v02.config import StrengthConfig


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_strength(
    effective_mass: float,
    velocity: float,
    acceleration: float,
    coherence: float,
    uncertainty: float,
    cfg: StrengthConfig,
) -> float:
    c = cfg.coefficients
    raw = (
        c["bias"]
        + c["mass"] * effective_mass
        + c["velocity"] * abs(velocity)
        + c["acceleration"] * abs(acceleration)
        + c["coherence"] * coherence
        - c["uncertainty"] * uncertainty
    )
    s = _sigmoid(raw)
    lo, hi = cfg.bounds
    return max(lo, min(hi, s))

