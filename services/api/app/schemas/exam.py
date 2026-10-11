from pydantic import BaseModel, ConfigDict


class BookletItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    physical_position: int
    area: str
    annulled: bool = False


class BookletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    exam_id: str
    day: int
    color: str
    language: str | None
    description: str
    paper_url: str | None = None
    pdf_download_url: str | None = None


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    year: int
    application: str
    title: str
    has_calibration: bool = True
    booklets: list[BookletOut] = []
