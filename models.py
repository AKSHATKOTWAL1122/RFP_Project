from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

# The brief specifies that a historical experience rating exists, but not its
# range. We fix it here as an explicit, documented assumption (0-5 inclusive).
EXPERIENCE_RATING_MIN = 0
EXPERIENCE_RATING_MAX = 5


class Criterion(BaseModel):
    criterion_id: int
    name: str
    description: str = ""
    weight: float
    max_score: float
    is_active: bool = True


class CriterionResult(BaseModel):
    criterion_id: Optional[int] = None
    score: float
    max_score: Optional[float] = None
    justification: str = ""
    evidence: str = ""


class LLMEvaluationOutput(BaseModel):
    supplier_name: str
    criteria: List[CriterionResult] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    overall_summary: str = ""


class ScoredCriterion(BaseModel):
    criterion: Criterion
    score: float
    benchmark: Optional[float] = None
    gap: Optional[float] = None
    relative_pct: Optional[float] = None
    justification: str = ""
    evidence: str = ""


class SupplierScore(BaseModel):
    supplier_name: str
    submission_date: date
    experience_rating: float
    criteria_snapshot: List[Criterion]
    scored_criteria: List[ScoredCriterion] = Field(default_factory=list)
    absolute_score: Optional[float] = None
    ppi: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    failed: bool = False
    risks: List[str] = Field(default_factory=list)
    overall_summary: str = ""


class RankedSupplier(BaseModel):
    supplier_score: SupplierScore
    ppi: Optional[float] = None
    final_rank: Optional[int] = None
