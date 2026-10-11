from pydantic import BaseModel, ConfigDict
from typing import Any


class InepImportRequest(BaseModel):
    year: int
    dataset_manifest_url: str | None = None
    checksum_sha256: str | None = None


class CalibrationRequest(BaseModel):
    exam_year: int
    application: str = "regular"
    area: str
    irt_model: str = "3PL"
    dataset_sha256: str
    code_version: str = "tri-core-0.1.0"


class CalibrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    calibration_id: str
    exam_year: int
    application: str
    area: str
    scale_alpha: float
    scale_beta: float
    status: str
    validation_metrics: dict[str, Any]
    dataset_sha256: str
    code_version: str
    official_algorithm: bool
