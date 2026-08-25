"""
Module/File Name: sade/pricing_pipeline/pipeline.py
Date Created / Migrated: August 25, 2026
Purpose:
    Orchestrate SADE Price-side mathematics and PriceEngine emission generation.
Executive Overview:
    Consumes adaptive pipeline output rows, maintains causal price history, computes
    p/p1/p2, fits F4 dynamics, performs one-step RK45 projection, assembles
    PriceEngine numerical payload, and emits PriceEmission.
Role in SADE:
    SADE-owned pricing pipeline boundary downstream of adaptive pipeline output.
Inputs:
    Per-observation adaptive output/context records.
Outputs:
    Per-observation pricing step result dictionaries and summary counters.
Parameters / Configuration:
    PricingPipelineConfig and migrated PriceEngine policy/cockpit configuration.
Persistent State:
    Causal observation history, derivative arrays, policy state, cockpit state,
    and run-level counters.
External Dependencies:
    numpy, scipy, and sade.pricing_pipeline.price_engine package.
Main Callers / Consumers:
    SADE pricing unit run wiring and integration tests.
Important Assumptions:
    Source timestamps are consumed as provided; no normalization or cadence logic
    is added. RK45 projection horizon is fixed to one minute and is distinct from
    source timestamp spacing.
Scientific Provenance:
    Consolidates migrated behavior from:
    - APTF diagnostics/run_test_009_derivative_analysis.py::causal_quadratic
    - APTF diagnostics/run_test_013b_qqq_validation.py::fit_f4
    - APTF diagnostics/run_test_013b_qqq_validation.py::solve_cover
    - APTF diagnostics/run_test_014_policy_development.py::build_numerical
    - APTF price_engine package
Explicit Exclusions / What This Module Does NOT Do:
    - No SDX client usage
    - No volume processing
    - No final BUY/HOLD/SELL execution decision synthesis
Failure / Error Behavior:
    Raises explicit errors for missing fields, entity mismatch, source-order
    regression, malformed numerical payload/PriceEngine coherence failures, and
    serialization failures.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from .derivatives import causal_quadratic
from .dynamics import fit_f4, valid_fit
from .numerical import build_numerical_row
from .projection import solve_cover
from .price_engine import (
    CockpitPolicyConfig,
    CockpitState,
    EmissionPolicy,
    MarketObservation,
    PolicyConfig,
    PolicyState,
    PriceCockpitInterpreter,
    PriceEngine,
)


REQUIRED_ADAPTIVE_FIELDS = (
    "entity_id",
    "source_row_index",
    "source_timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True)
class PricingPipelineConfig:
    """Configuration for SADE pricing pipeline orchestration.

    Purpose:
        Hold migration-frozen mathematical settings and metadata defaults.
    Arguments / Inputs:
        entity, derivative/F4 settings, RK45 tolerance, and metadata defaults.
    Returns / Outputs:
        Immutable pricing pipeline configuration.
    Persistent State Changes:
        None.
    Side Effects:
        None.
    Assumptions:
        Window and tolerance settings match validated mathematical behavior.
    Failure / Error Behavior:
        Raises ValueError for invalid configuration values.
    Scientific Meaning:
        Encodes execution settings only; no scientific mutation.
    """

    entity: str
    derivative_window: int = 15
    f4_window: int = 30
    epsilon: float = 0.0035332071428566536
    ridge_lambda: float = 1.0
    rtol: float = 1e-6
    default_session: str = "UNKNOWN"
    default_source_provider: str = "SDX_V1_1_STREAM"
    enable_cockpit: bool = True

    def __post_init__(self) -> None:
        if not self.entity.strip():
            raise ValueError("CONFIG_INVALID entity must be non-empty")
        if self.derivative_window < 2:
            raise ValueError("CONFIG_INVALID derivative_window must be >= 2")
        if self.f4_window < 3:
            raise ValueError("CONFIG_INVALID f4_window must be >= 3")
        if self.epsilon <= 0:
            raise ValueError("CONFIG_INVALID epsilon must be > 0")
        if self.ridge_lambda < 0:
            raise ValueError("CONFIG_INVALID ridge_lambda must be >= 0")
        if self.rtol <= 0:
            raise ValueError("CONFIG_INVALID rtol must be > 0")


class PricingPipeline:
    """Run one causal SADE pricing stream.

    Purpose:
        Preserve migrated Price mathematics while consuming adaptive output rows.
    Arguments / Inputs:
        config and optional policy/cockpit configurations.
    Returns / Outputs:
        Stateful pricing pipeline object.
    Persistent State Changes:
        Maintains historical arrays and policy/cockpit states.
    Side Effects:
        None.
    Assumptions:
        process is called in source-causal order.
    Failure / Error Behavior:
        Raises explicit validation/runtime errors described in process().
    Scientific Meaning:
        Orchestrates migrated math exactly; does not invent new model components.
    """

    def __init__(
        self,
        config: PricingPipelineConfig,
        policy_config: PolicyConfig | None = None,
        cockpit_config: CockpitPolicyConfig | None = None,
    ) -> None:
        self.config = config

        self._policy = EmissionPolicy(
            policy_config
            if policy_config is not None
            else PolicyConfig(
                policy_id="P_EMISSION_V0_1",
                epsilon=config.epsilon,
                condition_median=7.835779770603297,
                condition_q95=13.040323846425492,
                eigenvalue_median=0.42217565243576405,
                eigenvalue_q95=0.6449378901835623,
                amplification_median=2.2423650649621742,
                amplification_q95=2.6637448484678754,
                direct_reversal_debounce=True,
            )
        )
        self._engine = PriceEngine(self._policy)
        self._policy_state = PolicyState()

        self._cockpit: PriceCockpitInterpreter | None = None
        self._cockpit_state = CockpitState()
        if config.enable_cockpit:
            cockpit_cfg = cockpit_config or CockpitPolicyConfig(
                policy_id="TRANSITION_EVIDENCE_P1",
                epsilon=config.epsilon,
                zero_proximity_threshold=0.9,
                deceleration_strength_threshold=0.05,
                persistence_observations=1,
                candidate_hold_observations=0,
                low_confidence_requires_amber=False,
                domain_exit_requires_amber=False,
            )
            self._cockpit = PriceCockpitInterpreter(cockpit_cfg)

        self._source_row_index: list[int] = []
        self._timestamps: list[str] = []
        self._times_minutes: list[float] = []
        self._opens: list[float] = []
        self._highs: list[float] = []
        self._lows: list[float] = []
        self._closes: list[float] = []
        self._volumes: list[float] = []

        self._summary: dict[str, Any] = {
            "observations_received": 0,
            "warmup_observations": 0,
            "derivative_ready_observations": 0,
            "f4_ready_observations": 0,
            "rk45_attempts": 0,
            "rk45_successes": 0,
            "rk45_failures": 0,
            "domain_exits": 0,
            "price_emissions_generated": 0,
            "price_cockpit_outputs": 0,
            "trajectory_phase_counts": Counter(),
            "turning_tendency_counts": Counter(),
            "confidence_state_counts": Counter(),
            "price_color_counts": Counter(),
            "step_status_counts": Counter(),
        }

    def process(self, adaptive_record: dict[str, Any]) -> dict[str, Any]:
        """Process one adaptive output record through pricing pipeline.

        Purpose:
            Execute full migrated pricing path for one causal observation.
        Arguments / Inputs:
            adaptive_record with required adaptive output fields.
        Returns / Outputs:
            Step result dictionary with status, optional emission, optional cockpit
            emission, and optional numerical payload.
        Persistent State Changes:
            Appends history and advances internal policy/cockpit state.
        Side Effects:
            None.
        Assumptions:
            Caller provides records in source order from adaptive pipeline.
        Failure / Error Behavior:
            Raises ValueError/RuntimeError for explicit hard-failure conditions.
        Scientific Meaning:
            Applies migrated derivative -> F4 -> RK45 -> numerical -> PriceEngine flow.
        """

        for name in REQUIRED_ADAPTIVE_FIELDS:
            if name not in adaptive_record:
                raise ValueError(f"MISSING_ADAPTIVE_FIELD {name}")

        entity = str(adaptive_record["entity_id"])
        if entity != self.config.entity:
            raise ValueError(f"ENTITY_MISMATCH expected={self.config.entity} got={entity}")

        source_row = int(adaptive_record["source_row_index"])
        if self._source_row_index and source_row != self._source_row_index[-1] + 1:
            raise ValueError(
                "SOURCE_ORDER_REGRESSION "
                f"expected={self._source_row_index[-1] + 1} got={source_row}"
            )

        timestamp = str(adaptive_record["source_timestamp"])
        self._source_row_index.append(source_row)
        self._timestamps.append(timestamp)
        self._times_minutes.append(self._to_minutes(timestamp))
        self._opens.append(float(adaptive_record["open"]))
        self._highs.append(float(adaptive_record["high"]))
        self._lows.append(float(adaptive_record["low"]))
        self._closes.append(float(adaptive_record["close"]))
        self._volumes.append(float(adaptive_record["volume"]))

        self._summary["observations_received"] += 1
        index = len(self._closes) - 1
        active_index = index - 1

        if active_index < 0:
            return self._step_result("WARMUP_DERIVATIVE", index=index)

        p = np.asarray(self._closes, dtype=float)
        times_minutes = np.asarray(self._times_minutes, dtype=float)
        p1, p2, _failures = causal_quadratic(times_minutes, p, self.config.derivative_window)

        if not (np.isfinite(p1[active_index]) and np.isfinite(p2[active_index])):
            return self._step_result("WARMUP_DERIVATIVE", index=active_index)

        self._summary["derivative_ready_observations"] += 1

        jp = np.full(len(p), np.nan)
        for i in range(1, len(p)):
            if np.isfinite(p2[i - 1]) and np.isfinite(p2[i]):
                jp[i] = p2[i] - p2[i - 1]

        if active_index < self.config.f4_window or not np.all(
            np.isfinite(jp[active_index - self.config.f4_window + 1 : active_index + 1])
        ):
            return self._step_result("WARMUP_F4", index=active_index)

        fit = fit_f4(p, p1, p2, jp, self.config.f4_window, self.config.ridge_lambda)
        if not valid_fit(fit, active_index):
            return self._step_result("F4_FIT_UNAVAILABLE", index=active_index)

        self._summary["f4_ready_observations"] += 1
        self._summary["rk45_attempts"] += 1

        solved, failed = solve_cover([active_index], fit, p, p1, p2, False, self.config.rtol, self.config.epsilon)
        numerical = build_numerical_row(
            index=active_index,
            entity=entity,
            timestamp=self._timestamps[active_index],
            session=str(adaptive_record.get("session_type", self.config.default_session)),
            open_value=self._opens[active_index],
            high_value=self._highs[active_index],
            low_value=self._lows[active_index],
            close_value=self._closes[active_index],
            volume_value=self._volumes[active_index],
            source_provider=str(adaptive_record.get("source_provider", self.config.default_source_provider)),
            fit=fit,
            solved=solved,
            failed=failed,
            p=p,
            p1=p1,
            p2=p2,
        )

        if numerical["rk_success"]:
            self._summary["rk45_successes"] += 1
        else:
            self._summary["rk45_failures"] += 1
        if numerical["domain_exit"]:
            self._summary["domain_exits"] += 1

        observation = MarketObservation(
            symbol=entity,
            timestamp=self._timestamps[active_index],
            open=self._opens[active_index],
            high=self._highs[active_index],
            low=self._lows[active_index],
            close=self._closes[active_index],
            volume=self._volumes[active_index],
            session=str(adaptive_record.get("session_type", self.config.default_session)),
            source=str(adaptive_record.get("source_provider", self.config.default_source_provider)),
        )

        try:
            emission, self._policy_state = self._engine.observe(observation, numerical, self._policy_state)
        except Exception as error:
            raise RuntimeError(f"PRICE_ENGINE_FAILURE index={active_index + 1}: {error}") from error

        self._summary["price_emissions_generated"] += 1
        self._summary["trajectory_phase_counts"][emission.trajectory_phase] += 1
        self._summary["turning_tendency_counts"][emission.turning_tendency] += 1
        self._summary["confidence_state_counts"][emission.confidence_state] += 1
        self._summary["price_color_counts"][emission.color] += 1

        cockpit_payload = None
        if self._cockpit is not None:
            cockpit_emission, self._cockpit_state = self._cockpit.observe(emission, self._cockpit_state)
            cockpit_payload = cockpit_emission.as_dict()
            self._summary["price_cockpit_outputs"] += 1

        status = "EMITTED" if numerical["rk_success"] else "RK45_FAILURE"
        return self._step_result(
            status,
            index=active_index,
            numerical=numerical,
            price_emission=emission.as_dict(),
            cockpit_emission=cockpit_payload,
        )

    def summary(self) -> dict[str, Any]:
        """Return JSON-serializable summary counters for current pipeline state."""

        payload: dict[str, Any] = {}
        for key, value in self._summary.items():
            payload[key] = dict(value) if isinstance(value, Counter) else value
        return payload

    def close(self) -> dict[str, Any]:
        """Finalize and return summary.

        Purpose:
            Provide caller a stable terminal summary of pricing pipeline execution.
        Arguments / Inputs:
            None.
        Returns / Outputs:
            Summary dictionary.
        Persistent State Changes:
            None.
        Side Effects:
            None.
        Assumptions:
            Caller handles persistence.
        Failure / Error Behavior:
            None.
        Scientific Meaning:
            Reporting only.
        """

        return self.summary()

    def _step_result(
        self,
        status: str,
        *,
        index: int,
        numerical: dict[str, Any] | None = None,
        price_emission: dict[str, Any] | None = None,
        cockpit_emission: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._summary["step_status_counts"][status] += 1
        if status.startswith("WARMUP"):
            self._summary["warmup_observations"] += 1
        return {
            "status": status,
            "observation_index": index + 1,
            "entity": self.config.entity,
            "source_timestamp": self._timestamps[index],
            "numerical": numerical,
            "price_emission": price_emission,
            "cockpit_emission": cockpit_emission,
        }

    @staticmethod
    def _to_minutes(timestamp_text: str) -> float:
        value = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
        return value.timestamp() / 60.0
