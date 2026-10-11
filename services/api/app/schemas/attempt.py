from pydantic import BaseModel, Field, ConfigDict


class AttemptCreate(BaseModel):
    booklet_id: str


class ResponseItemInput(BaseModel):
    position: int = Field(ge=1, le=180)
    answer: str | None = Field(default=None, pattern="^[A-Ea-e]?$")
    is_correct: bool | None = None
    source: str = "manual"


class AttemptResponsesUpdate(BaseModel):
    responses: list[ResponseItemInput]


class ResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    physical_position: int
    selected_answer: str | None
    is_correct: bool | None
    source: str
    confidence: float | None


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    booklet_id: str
    status: str
    responses: list[ResponseOut] = []
