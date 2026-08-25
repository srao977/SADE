from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContextRole(str, Enum):
    PRODUCTION = "PRODUCTION"
    TEST_FIXTURE = "TEST_FIXTURE"


class InputProvenance(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    STATE = "STATE"
    MATHEMATICAL_CONSTANT = "MATHEMATICAL_CONSTANT"
    TEST_FIXTURE = "TEST_FIXTURE"
    UNAVAILABLE = "UNAVAILABLE"


CONTEXT_VALUE_FIELDS = (
    "evaluation_time",
    "market_eligible",
)


class EnvelopeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    context_role: ContextRole = ContextRole.TEST_FIXTURE
    provenance: dict[str, InputProvenance] = Field(default_factory=dict)
    evaluation_time: float
    market_eligible: bool | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> "EnvelopeContext":
        if self.context_role == ContextRole.TEST_FIXTURE and not self.provenance:
            self.provenance = {
                name: (
                    InputProvenance.TEST_FIXTURE
                    if getattr(self, name) is not None
                    else InputProvenance.UNAVAILABLE
                )
                for name in CONTEXT_VALUE_FIELDS
            }
        if set(self.provenance) != set(CONTEXT_VALUE_FIELDS):
            raise ValueError("context provenance must classify all current value fields")
        for name in CONTEXT_VALUE_FIELDS:
            value = getattr(self, name)
            source = self.provenance[name]
            if value is None and source != InputProvenance.UNAVAILABLE:
                raise ValueError(f"null context field must be UNAVAILABLE: {name}")
            if value is not None and source == InputProvenance.UNAVAILABLE:
                raise ValueError(f"UNAVAILABLE context field must be null: {name}")
            if self.context_role == ContextRole.PRODUCTION and source == InputProvenance.TEST_FIXTURE:
                raise ValueError(f"production context cannot use TEST_FIXTURE provenance: {name}")
        return self

    @classmethod
    def production(
        cls,
        *,
        evaluation_time: float,
        values: dict[str, Any] | None = None,
        provenance: dict[str, InputProvenance | str] | None = None,
    ) -> "EnvelopeContext":
        supplied = dict(values or {})
        sources = {
            name: InputProvenance.UNAVAILABLE for name in CONTEXT_VALUE_FIELDS
        }
        sources["evaluation_time"] = InputProvenance.DERIVED
        for name, source in (provenance or {}).items():
            if name not in CONTEXT_VALUE_FIELDS:
                raise ValueError(f"unknown context provenance field: {name}")
            sources[name] = InputProvenance(source)
        return cls(
            context_role=ContextRole.PRODUCTION,
            provenance=sources,
            evaluation_time=evaluation_time,
            **supplied,
        )


