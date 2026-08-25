from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from sade.d01.v02.state import RuntimeState


def state_hash(snapshot: dict[str, object]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def to_snapshot(state: RuntimeState, config_hash: str, model_version: str) -> dict[str, object]:
    payload = {
        "entity_id": state.entity_id,
        "model_version": model_version,
        "model_time": state.model_time,
        "observation_sequence": state.sequence,
        "adaptive_reference": state.adaptive_reference,
        "adaptive_scale": state.adaptive_scale,
        "state_vector": asdict(state.state_vector),
        "adaptive_parameters": dict(state.parameter_state),
        "half_life_state": asdict(state.half_life_state),
        "uncertainty_state": state.state_vector.uncertainty,
        "previous_observation": None if state.last_observation is None else asdict(state.last_observation),
        "configuration_hash": config_hash,
    }
    payload["state_hash"] = state_hash(payload)
    return payload


def from_snapshot(snapshot: dict[str, object], state: RuntimeState) -> RuntimeState:
    state.model_time = float(snapshot["model_time"])
    state.sequence = int(snapshot["observation_sequence"])
    state.adaptive_reference = float(snapshot["adaptive_reference"])
    state.adaptive_scale = float(snapshot["adaptive_scale"])
    state.parameter_state = dict(snapshot["adaptive_parameters"])
    return state

