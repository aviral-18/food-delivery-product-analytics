"""Request schemas for analytics actions (decision lab, SQL explorer, exports)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LeverSpec(BaseModel):
    lever: str = Field(..., description="Lever name (see /decision-lab/levers).")
    magnitude: float = Field(..., description="Lever magnitude; units depend on the lever.")


class DecisionScenario(BaseModel):
    levers: list[LeverSpec] = Field(default_factory=list)


class SqlExecuteRequest(BaseModel):
    sql: str = Field(..., description="A single read-only SELECT / WITH query.")
    limit: int = Field(200, ge=1, le=5000)


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None
