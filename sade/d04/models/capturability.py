from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CapturabilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_eligibility: int = Field(ge=0, le=1)
    geometry_quality: float = Field(ge=0.0, le=1.0)
    structural_quality: float = Field(ge=0.0, le=1.0)
    risk_quality: float = Field(ge=0.0, le=1.0)
    base_capturability_score: float = Field(ge=0.0, le=1.0)
    capturability_score: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)

