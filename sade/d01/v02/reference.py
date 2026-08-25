from __future__ import annotations

from sade.d01.v02.config import ReferenceConfig


def update_reference_and_scale(
    price: float,
    prev_reference: float,
    prev_scale: float,
    cfg: ReferenceConfig,
) -> tuple[float, float]:
    ref = prev_reference + cfg.alpha * (price - prev_reference)
    abs_err = abs(price - ref)
    scale = max(cfg.min_scale, (0.95 * prev_scale) + (0.05 * abs_err))
    return ref, scale

