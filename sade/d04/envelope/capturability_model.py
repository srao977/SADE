from __future__ import annotations

from abc import ABC, abstractmethod
import math

from sade.d04.models.capturability import CapturabilityResult
from sade.d04.models.envelope_context import EnvelopeContext
from sade.d02.v02.models import PathDirection, ReturnShape


class InvalidReturnShapeError(ValueError):
    pass


class CapturabilityModel(ABC):
    @abstractmethod
    def evaluate(self, return_shape: ReturnShape, context: EnvelopeContext) -> CapturabilityResult:
        raise NotImplementedError


class CapturabilityModelV0_2(CapturabilityModel):
    @staticmethod
    def validate_return_shape(return_shape: ReturnShape) -> None:
        terminal = return_shape.forward_samples[-1].level - return_shape.current_level
        maximum = max(
            abs(sample.level - return_shape.current_level)
            for sample in return_shape.forward_samples
        )
        if return_shape.terminal_displacement > 0.0:
            direction = PathDirection.UPWARD
        elif return_shape.terminal_displacement < 0.0:
            direction = PathDirection.DOWNWARD
        else:
            direction = PathDirection.FLAT
        if (
            abs(return_shape.terminal_displacement) > return_shape.maximum_absolute_displacement
            or return_shape.terminal_displacement != terminal
            or return_shape.maximum_absolute_displacement != maximum
            or return_shape.path_direction != direction
        ):
            raise InvalidReturnShapeError("INVALID_RETURNSHAPE")

    @staticmethod
    def geometry_quality(return_shape: ReturnShape) -> float:
        maximum = return_shape.maximum_absolute_displacement
        if maximum == 0.0:
            return 0.0
        return abs(return_shape.terminal_displacement) / maximum

    @staticmethod
    def structural_quality(return_shape: ReturnShape) -> float:
        return (return_shape.strength * return_shape.coherence * return_shape.persistence) ** (1.0 / 3.0)

    @staticmethod
    def risk_quality(return_shape: ReturnShape) -> float:
        return math.sqrt((1.0 - return_shape.uncertainty) * (1.0 - return_shape.reversal_propensity))

    def evaluate(self, return_shape: ReturnShape, context: EnvelopeContext) -> CapturabilityResult:
        self.validate_return_shape(return_shape)
        geometry = self.geometry_quality(return_shape)
        structural = self.structural_quality(return_shape)
        risk = self.risk_quality(return_shape)
        base = geometry * structural * risk
        projection_valid = context.evaluation_time <= return_shape.model_time + return_shape.projection_interval
        hard_eligibility = int(
            projection_valid
            and context.market_eligible is not False
        )
        final = hard_eligibility * base

        reasons: list[str] = []
        if return_shape.maximum_absolute_displacement == 0.0:
            reasons.append("ZERO_GEOMETRY")
        if return_shape.uncertainty > 0.5:
            reasons.append("UNCERTAINTY_HIGH")
        if return_shape.reversal_propensity > 0.5:
            reasons.append("REVERSAL_PROPENSITY_HIGH")
        if not projection_valid:
            reasons.append("SHAPE_STALE")
        if context.market_eligible is False:
            reasons.append("MARKET_INELIGIBLE")

        return CapturabilityResult(
            hard_eligibility=hard_eligibility,
            geometry_quality=geometry,
            structural_quality=structural,
            risk_quality=risk,
            base_capturability_score=base,
            capturability_score=final,
            reason_codes=sorted(set(reasons)),
        )


CapturabilityModelV0 = CapturabilityModelV0_2

