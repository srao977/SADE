from __future__ import annotations


def compute_coherence(evidence: dict[str, float], weights: dict[str, float], epsilon: float) -> float:
    num = 0.0
    den = 0.0
    for key, value in evidence.items():
        w = float(weights.get(key, 0.0))
        num += w * value
        den += w * abs(value)
    if den <= epsilon:
        return 0.0
    return max(0.0, min(1.0, abs(num) / (den + epsilon)))

