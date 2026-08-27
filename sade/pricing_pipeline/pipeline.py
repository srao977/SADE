"""
Module/File Name: sade/pricing_pipeline/pipeline.py
Date Created / Modified: August 27, 2026
Purpose:
    Orchestrate SADE Price-side mathematics and PriceEngine emission generation.
Executive Overview:
    Consumes adaptive pipeline output rows, maintains causal price history, computes
    the newly active p1/p2 and F4 fit once, performs one-step analytic projection,
    assembles PriceEngine numerical payload, and emits PriceEmission.
Role in SADE:
    SADE-owned pricing pipeline boundary downstream of adaptive pipeline output.
Inputs:
    Per-observation adaptive output/context records.
Outputs:
    Per-observation pricing step result dictionaries and summary counters.
Parameters / Configuration:
    PricingPipelineConfig and migrated PriceEngine policy/cockpit configuration.
Persistent State:
    Bounded causal observation/derivative windows, latest source index, policy
    state, cockpit state, and run-level counters.
External Dependencies:
    numpy, scipy, and sade.pricing_pipeline.price_engine package.
Main Callers / Consumers:
    SADE pricing unit run wiring and integration tests.
Important Assumptions:
    Source timestamps are consumed as provided; no normalization or cadence logic
    is added. The analytic projection horizon is fixed to one minute and is distinct from
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
    - No recomputation of prior derivative or F4 fits in the live path
Failure / Error Behavior:
    Raises explicit errors for missing fields, entity mismatch, source-order
    regression, malformed numerical payload/PriceEngine coherence failures, and
    serialization failures.
Solution Method Changed:
    YES; projection trajectory generation uses analytic matrix exponentiation.
ODE Equations Changed:
    NO
Scientific Mathematics Changed:
    NO
Computational Scheduling Changed:
    YES; each derivative and F4 fit is computed only when its index becomes active.
Historical Recomputation Removed:
    YES
Finding 001 Analytic Projection Changed:
    NO
Previous Retention:
    Every source, OHLCV, p1, p2, and jp value for the process lifetime.
New Retention:
    max(derivative_window, f4_window)+1 synchronized values; default 31.
Scientific State Removed:
    NO
Hot-Memory Behavior Changed:
    YES
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from .derivatives import causal_quadratic_at_index
from .dynamics import allocate_fit, fit_f4_at_index
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
    """Run one causal SADE pricing stream with bounded scientific history.

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
    Retention Semantics:
        Retains max(derivative_window, f4_window)+1 synchronized rows: one pending
        newest observation and the complete trailing window ending at unchanged
        active_index=current_index-1. Older rows never affect future calculations.
        External observation lineage uses the global stream count, never deque index.
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

        self._history_limit = max(config.derivative_window, config.f4_window) + 1
        self._last_source_row_index: int | None = None
        self._timestamps: deque[str] = deque(maxlen=self._history_limit)
        self._times_minutes: deque[float] = deque(maxlen=self._history_limit)
        self._opens: deque[float] = deque(maxlen=self._history_limit)
        self._highs: deque[float] = deque(maxlen=self._history_limit)
        self._lows: deque[float] = deque(maxlen=self._history_limit)
        self._closes: deque[float] = deque(maxlen=self._history_limit)
        self._volumes: deque[float] = deque(maxlen=self._history_limit)
        self._p1: deque[float] = deque(maxlen=self._history_limit)
        self._p2: deque[float] = deque(maxlen=self._history_limit)
        self._jp: deque[float] = deque(maxlen=self._history_limit)

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
            Advances bounded history, latest lineage, and policy/cockpit state.
        Side Effects:
            None.
        Assumptions:
            Caller provides records in source order from adaptive pipeline.
        Failure / Error Behavior:
            Raises ValueError/RuntimeError for explicit hard-failure conditions.
        Scientific Meaning:
                Applies derivative -> F4 -> analytic projection -> numerical -> PriceEngine flow.
            Legacy rk_success/rk45 summary names represent generic projection success
            and remain unchanged for downstream compatibility.
        Retention Semantics:
            At most max(derivative_window, f4_window)+1 aligned rows are retained;
            discarded rows cannot enter any future active trailing window.
        """

        for name in REQUIRED_ADAPTIVE_FIELDS:
            if name not in adaptive_record:
                raise ValueError(f"MISSING_ADAPTIVE_FIELD {name}")

        entity = str(adaptive_record["entity_id"])
        if entity != self.config.entity:
            raise ValueError(f"ENTITY_MISMATCH expected={self.config.entity} got={entity}")

        source_row = int(adaptive_record["source_row_index"])
        if self._last_source_row_index is not None and source_row != self._last_source_row_index + 1:
            raise ValueError(
                "SOURCE_ORDER_REGRESSION "
                f"expected={self._last_source_row_index + 1} got={source_row}"
            )
        self._last_source_row_index = source_row

        timestamp = str(adaptive_record["source_timestamp"])
        self._timestamps.append(timestamp)
        self._times_minutes.append(self._to_minutes(timestamp))
        self._opens.append(float(adaptive_record["open"]))
        self._highs.append(float(adaptive_record["high"]))
        self._lows.append(float(adaptive_record["low"]))
        self._closes.append(float(adaptive_record["close"]))
        self._volumes.append(float(adaptive_record["volume"]))
        self._p1.append(float("nan"))
        self._p2.append(float("nan"))
        self._jp.append(float("nan"))

        self._summary["observations_received"] += 1
        global_index = self._summary["observations_received"] - 1
        global_active_index = global_index - 1
        index = len(self._closes) - 1
        active_index = index - 1

        if active_index < 0:
            return self._step_result("WARMUP_DERIVATIVE", index=index, logical_index=global_index)

        p = np.asarray(self._closes, dtype=float)
        times_minutes = np.asarray(self._times_minutes, dtype=float)
        active_p1, active_p2, _failures = causal_quadratic_at_index(
            times_minutes,
            p,
            active_index,
            self.config.derivative_window,
        )
        self._p1[active_index] = active_p1
        self._p2[active_index] = active_p2
        p1 = np.asarray(self._p1, dtype=float)
        p2 = np.asarray(self._p2, dtype=float)

        if not (np.isfinite(p1[active_index]) and np.isfinite(p2[active_index])):
            return self._step_result(
                "WARMUP_DERIVATIVE",
                index=active_index,
                logical_index=global_active_index,
            )

        self._summary["derivative_ready_observations"] += 1

        if active_index > 0 and np.isfinite(p2[active_index - 1]):
            self._jp[active_index] = p2[active_index] - p2[active_index - 1]
        jp = np.asarray(self._jp, dtype=float)

        if global_active_index < self.config.f4_window or not np.all(
            np.isfinite(jp[active_index - self.config.f4_window + 1 : active_index + 1])
        ):
            return self._step_result("WARMUP_F4", index=active_index, logical_index=global_active_index)

        active_fit = fit_f4_at_index(
            p,
            p1,
            p2,
            jp,
            active_index,
            self.config.f4_window,
            self.config.ridge_lambda,
        )
        if active_fit is None:
            return self._step_result(
                "F4_FIT_UNAVAILABLE",
                index=active_index,
                logical_index=global_active_index,
            )

        fit = allocate_fit(len(p), 4)
        for name, value in active_fit.items():
            fit[name][active_index] = value

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
        numerical["index"] = global_active_index
        numerical["observation_index"] = global_active_index + 1

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
            raise RuntimeError(f"PRICE_ENGINE_FAILURE index={global_active_index + 1}: {error}") from error

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
            logical_index=global_active_index,
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
        logical_index: int,
        numerical: dict[str, Any] | None = None,
        price_emission: dict[str, Any] | None = None,
        cockpit_emission: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._summary["step_status_counts"][status] += 1
        if status.startswith("WARMUP"):
            self._summary["warmup_observations"] += 1
        return {
            "status": status,
            "observation_index": logical_index + 1,
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
