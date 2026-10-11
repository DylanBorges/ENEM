from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    attempt_id: str | None = None
    report_type: str = "STUDENT_INDIVIDUAL"


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    attempt_id: str | None
    report_type: str
    status: str
    file_path: str | None
    download_url: str | None = None
