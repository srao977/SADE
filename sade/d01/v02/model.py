from __future__ import annotations

import hashlib
import json
import math

from sade.d01.v02.adaptation import update_parameters
from sade.d01.v02.coherence import compute_coherence
from sade.d01.v02.config import D01V02Config
from sade.d01.v02.forward import compute_forward_interval, forward_samples, propagate_level
from sade.d01.v02.half_life import adapt_half_life
from sade.d01.v02.health import evaluate_health
from sade.d01.v02.innovation import innovation_magnitude
from sade.d01.v02.kinematics import compute_kinematics
from sade.d01.v02.observations import NormalizedObservation, assert_causal_sequence
from sade.d01.v02.outputs import DMOOutput, FMOSample, FMOOutput
from sade.d01.v02.persistence import update_persistence
from sade.d01.v02.perturbation import (
    PERTURBATION_STRUCTURAL,
    classify_perturbation,
)
from sade.d01.v02.reference import update_reference_and_scale
from sade.d01.v02.reversal import compute_reversal_propensity
from sade.d01.v02.snapshot import to_snapshot
from sade.d01.v02.state import HalfLifeState, RuntimeState
from sade.d01.v02.strength import compute_strength
from sade.d01.v02.trace import TraceRecord
from sade.d01.v02.uncertainty import compute_uncertainty
from sade.d01.v02.volume import update_volume_influence


class D01V02Model:
    def __init__(self, entity_id: str, config: D01V02Config | None = None) -> None:
        self.config = config or D01V02Config()
        self.config_hash = self.config.sha256()
        self.state = RuntimeState(entity_id=entity_id)
        self.state.half_life_state = HalfLifeState(
            observation_half_life=self.config.half_life.baseline,
            forward_half_life=self.config.half_life.baseline,
        )
        self.trace_records: list[TraceRecord] = []

    def _state_hash(self) -> str:
        payload = {
            "level": self.state.state_vector.level,
            "velocity": self.state.state_vector.velocity,
            "acceleration": self.state.state_vector.acceleration,
            "curvature": self.state.state_vector.curvature,
            "strength": self.state.state_vector.strength,
            "persistence": self.state.state_vector.persistence,
            "uncertainty": self.state.state_vector.uncertainty,
            "reversal_propensity": self.state.state_vector.reversal_propensity,
            "observation_half_life": self.state.half_life_state.observation_half_life,
            "forward_half_life": self.state.half_life_state.forward_half_life,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest().upper()

    def step(self, observation: NormalizedObservation) -> tuple[DMOOutput, FMOOutput]:
        obs = observation.with_defaults()

        # 1. Validate observation and causal sequence.
        assert_causal_sequence(self.state.last_observation, obs)

        # 2. Update availability/data-quality state.
        data_quality = max(0.0, min(1.0, obs.source_quality))

        # 3. Compute dt.
        if self.state.last_event_time is None:
            dt = 1.0
        else:
            dt = max(0.0, obs.event_time - self.state.last_event_time)
            if dt > 5.0:
                self.state.data_gap_count += 1
        prior_velocity = self.state.prev_velocity

        # 4. Update causal reference and scale.
        if self.state.sequence == 0:
            self.state.adaptive_reference = obs.price
            self.state.adaptive_scale = max(self.config.reference.min_scale, self.state.adaptive_scale)
        else:
            self.state.adaptive_reference, self.state.adaptive_scale = update_reference_and_scale(
                obs.price,
                self.state.adaptive_reference,
                self.state.adaptive_scale,
                self.config.reference,
            )

        # 5,6. Compute primitive normalized state and kinematics.
        level, velocity, acceleration, curvature, clipped = compute_kinematics(
            price=obs.price,
            reference=self.state.adaptive_reference,
            scale=self.state.adaptive_scale,
            prev_level=self.state.prev_level,
            prev_velocity=self.state.prev_velocity,
            dt=dt,
            cfg=self.config.kinematics,
            epsilon=self.config.numerical.epsilon,
        )
        self.state.clipping_count += clipped

        # 7,8. Compute expected observation/state and innovation.
        residual, innovation_mag = innovation_magnitude(
            level,
            self.state.prev_level,
            self.state.prev_velocity,
            dt,
            self.config.numerical.epsilon,
        )
        if innovation_mag > 5.0:
            self.state.innovation_extreme_count += 1

        # 9. Update volume/activity influence.
        volume_enabled = self.config.volume.enabled and self.config.ablation.volume_influence
        if volume_enabled:
            self.state.volume_reference, volume_influence = update_volume_influence(
                obs.volume,
                self.state.volume_reference,
                self.config.volume,
                self.config.numerical.epsilon,
            )
        else:
            volume_influence = 0.0

        # 10. Classify perturbation.
        perturbation_class, perturbation_magnitude, perturbation_multiplier = classify_perturbation(
            innovation=innovation_mag,
            prev_velocity=self.state.prev_velocity,
            velocity=velocity,
            source_quality=data_quality,
            cfg=self.config.perturbation,
            numerical_epsilon=self.config.numerical.epsilon,
            innovation_residual=residual,
            prior_level=self.state.prev_level,
        )

        # 11. Compute coherence.
        evidence = {
            "displacement": level,
            "velocity": velocity,
            "acceleration": acceleration,
            "volume": volume_influence if volume_enabled else 0.0,
        }
        coherence = compute_coherence(
            evidence,
            self.config.coherence.channel_weights,
            self.config.numerical.epsilon,
        )
        if not self.config.ablation.coherence_influence:
            coherence = 0.5

        # 12. Update strength.
        effective_mass = volume_influence
        uncertainty_for_strength = self.state.state_vector.uncertainty
        strength = compute_strength(
            effective_mass=effective_mass,
            velocity=velocity,
            acceleration=acceleration,
            coherence=coherence,
            uncertainty=uncertainty_for_strength,
            cfg=self.config.strength,
        )

        # 13. Update persistence.
        persistence = update_persistence(
            prev_persistence=self.state.state_vector.persistence,
            velocity=velocity,
            prev_velocity=self.state.prev_velocity,
            acceleration=acceleration,
            perturbation_class=perturbation_class,
            cfg=self.config.persistence,
        )

        # 14. Update uncertainty.
        unknown_perturbation = 1.0 if perturbation_class == PERTURBATION_STRUCTURAL else 0.0
        instability = min(1.0, abs(residual))
        uncertainty = compute_uncertainty(
            innovation_mag=innovation_mag,
            coherence=coherence,
            unknown_perturbation=unknown_perturbation,
            data_quality_degradation=1.0 - data_quality,
            instability=instability,
            cfg=self.config.uncertainty,
        )

        # 15. Update reversal propensity.
        if self.config.ablation.reversal_channel:
            reversal = compute_reversal_propensity(
                velocity=velocity,
                acceleration=acceleration,
                perturbation_class=perturbation_class,
                persistence=persistence,
                level=level,
                uncertainty=uncertainty,
                cfg=self.config.reversal,
            )
        else:
            reversal = 0.0

        # 16. Update half-life/relevance state.
        if self.config.ablation.adaptive_half_life:
            obs_hl = adapt_half_life(
                self.state.half_life_state.observation_half_life,
                persistence,
                strength,
                uncertainty,
                perturbation_class,
                self.config.half_life,
            )
            fwd_hl = adapt_half_life(
                self.state.half_life_state.forward_half_life,
                persistence,
                strength,
                uncertainty,
                perturbation_class,
                self.config.half_life,
            )
        else:
            obs_hl = self.config.half_life.baseline
            fwd_hl = self.config.half_life.baseline

        # 17. Update bounded adaptive parameters.
        adaptive_mult = perturbation_multiplier if self.config.ablation.perturbation_adaptation else 1.0
        updated_params, update_mag, bound_hits = update_parameters(
            params=self.state.parameter_state,
            uncertainty=uncertainty,
            strength=strength,
            perturbation_multiplier=adaptive_mult,
            cfg=self.config.adaptation,
        )
        self.state.parameter_state = updated_params
        self.state.parameter_update_magnitude = update_mag
        self.state.parameter_bound_hits += bound_hits

        # Apply the adaptive parameter to reference smoothing rate.
        ref_alpha = self.state.parameter_state.get("ref_alpha", self.config.reference.alpha)
        self.state.parameter_state["ref_alpha"] = max(0.001, min(0.2, ref_alpha))

        # Update runtime state before output assembly.
        self.state.model_time = obs.event_time
        self.state.sequence += 1
        self.state.last_event_time = obs.event_time
        self.state.last_observation = obs
        self.state.prev_level = level
        self.state.prev_velocity = velocity
        self.state.state_vector.level = level
        self.state.state_vector.velocity = velocity
        self.state.state_vector.acceleration = acceleration
        self.state.state_vector.curvature = curvature
        self.state.state_vector.strength = strength
        self.state.state_vector.persistence = persistence
        self.state.state_vector.perturbation_magnitude = perturbation_magnitude
        self.state.state_vector.uncertainty = uncertainty
        self.state.state_vector.reversal_propensity = reversal
        self.state.half_life_state.observation_half_life = obs_hl
        self.state.half_life_state.forward_half_life = fwd_hl

        # 18,19. Build current DMO and generate elastic FMO.
        if self.config.ablation.elastic_forward_interval:
            interval_length = compute_forward_interval(
                baseline=self.config.forward.baseline_interval,
                persistence=persistence,
                strength=strength,
                uncertainty=uncertainty,
                perturbation_magnitude=perturbation_magnitude,
                cfg=self.config.forward,
            )
        else:
            interval_length = self.config.forward.baseline_interval
        taus = forward_samples(interval_length, self.config.forward.sample_count, self.config.forward.sampling_exponent)

        samples: list[FMOSample] = []
        for tau in taus:
            decay = 2.0 ** (-tau / max(self.config.numerical.epsilon, fwd_hl))
            proj_unc = max(0.0, min(1.0, uncertainty + (1.0 - decay) * 0.15))
            samples.append(
                FMOSample(
                    tau=tau,
                    level=propagate_level(level, velocity, acceleration, tau),
                    velocity=velocity * decay,
                    uncertainty=proj_unc,
                    strength=max(0.0, min(1.0, strength * decay)),
                    persistence=max(0.0, min(1.0, persistence * decay)),
                    reversal_propensity=max(0.0, min(1.0, reversal + (1.0 - decay) * 0.1)),
                )
            )

        # 20. Run numerical/model-health assertions.
        health_status = evaluate_health(self.state)

        state_support_ratio = (strength * persistence) / max(
            self.config.numerical.epsilon,
            uncertainty + reversal,
        )
        trace_id = f"{self.state.entity_id}:{self.state.sequence}"

        dmo = DMOOutput(
            model_time=self.state.model_time,
            entity_id=self.state.entity_id,
            model_version=self.config.model_version,
            state_level=level,
            state_velocity=velocity,
            state_acceleration=acceleration,
            state_curvature=curvature,
            strength=strength,
            coherence=coherence,
            persistence=persistence,
            perturbation_magnitude=perturbation_magnitude,
            perturbation_class=perturbation_class,
            uncertainty=uncertainty,
            reversal_propensity=reversal,
            state_support_ratio=state_support_ratio,
            observation_half_life=obs_hl,
            forward_half_life=fwd_hl,
            parameter_state=dict(self.state.parameter_state),
            parameter_update_magnitude=dict(self.state.parameter_update_magnitude),
            data_quality=data_quality,
            model_health=health_status,
            dmo_schema_version=self.config.dmo_schema_version,
            fmo_schema_version=self.config.fmo_schema_version,
            config_hash=self.config_hash,
            state_hash=self._state_hash(),
            trace_id=trace_id,
        )
        fmo = FMOOutput(
            model_time=self.state.model_time,
            entity_id=self.state.entity_id,
            interval_length=interval_length,
            samples=samples,
        )

        # 21. Persist trace/snapshot metadata.
        self.trace_records.append(
            TraceRecord(
                trace_id=trace_id,
                model_time=self.state.model_time,
                sequence=self.state.sequence,
                innovation_magnitude=innovation_mag,
                perturbation_materiality_floor=math.sqrt(max(0.0, self.config.numerical.epsilon)),
                perturbation_detected=(
                    perturbation_magnitude > math.sqrt(max(0.0, self.config.numerical.epsilon))
                    or data_quality < self.config.perturbation.structural_quality_floor
                ),
                prior_velocity=prior_velocity,
                current_velocity=velocity,
                velocity_change=velocity - prior_velocity,
                source_quality=data_quality,
                perturbation_class=perturbation_class,
                perturbation_magnitude=perturbation_magnitude,
                strength=strength,
                uncertainty=uncertainty,
                persistence=persistence,
                reversal_propensity=reversal,
                observation_half_life=obs_hl,
                forward_half_life=fwd_hl,
            )
        )

        # 22. Return versioned output.
        return dmo, fmo

    def snapshot(self) -> dict[str, object]:
        return to_snapshot(self.state, config_hash=self.config_hash, model_version=self.config.model_version)

