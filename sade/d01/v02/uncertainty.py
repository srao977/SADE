from __future__ import annotations

import math

from sade.d01.v02.config import UncertaintyConfig


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_uncertainty(
    innovation_mag: float,
    coherence: float,
    unknown_perturbation: float,
    data_quality_degradation: float,
    instability: float,
    cfg: UncertaintyConfig,
) -> float:
    c = cfg.coefficients
    raw = (
        c["innovation"] * innovation_mag
        + c["incoherence"] * (1.0 - coherence)
        + c["unknown_perturbation"] * unknown_perturbation
        + c["data_quality"] * data_quality_degradation
        + c["instability"] * instability
    )
    value = _sigmoid(raw - 1.0)
    lo, hi = cfg.bounds
    return max(lo, min(hi, value))

