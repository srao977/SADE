from __future__ import annotations

import math

from sade.d01.v02.config import VolumeConfig


def update_volume_influence(volume: float, prev_reference: float, cfg: VolumeConfig, epsilon: float) -> tuple[float, float]:
    ref = (1.0 - cfg.reference_alpha) * prev_reference + cfg.reference_alpha * volume
    relative = math.log1p(volume / max(ref, epsilon))
    absolute = math.log1p(max(volume, 0.0)) / 10.0
    v_star = relative + absolute
    lo, hi = cfg.influence_bounds
    v_star = max(lo, min(hi, v_star))
    return ref, v_star

