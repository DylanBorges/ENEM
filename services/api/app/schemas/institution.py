from pydantic import BaseModel, ConfigDict
from typing import Any


class CohortOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    year: int
    student_count: int


class InstitutionDashboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution_id: str
    name: str
    total_students: int
    total_attempts: int
    mean_estimated_score: float
    median_estimated_score: float
    distribution_by_area: dict[str, dict[str, Any]]
    cohorts: list[CohortOut] = []
