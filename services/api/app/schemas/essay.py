from pydantic import BaseModel, Field


class EssayCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=255)
    text: str = Field(min_length=100, max_length=30000)
    source: str = Field(default="typed", pattern="^typed$")


class CompetencyPrediction(BaseModel):
    competency: str
    predicted_score: int
    probabilities: dict[str, float]
    confidence: float
    feedback: str
    evidence_spans: list[str] = []
    requires_human_review: bool = False


class EssayPregradeResponse(BaseModel):
    submission_id: str
    status: str
    total_score: int
    competencies: list[CompetencyPrediction]
    official: bool = False
    model_version: str
    disclaimer: str = (
        "Pré-avaliação pedagógica preliminar gerada por inteligência artificial. "
        "Não constitui nota oficial do INEP ou correção humana definitiva."
    )


class HumanReviewRequest(BaseModel):
    reviewer_notes: str | None = None


class EssayDetailResponse(BaseModel):
    id: str
    topic: str
    text: str
    status: str
    created_at: str
    total_score: int | None = None
    competencies: list[CompetencyPrediction] = []
    model_version: str | None = None
    disclaimer: str = (
        "Pré-avaliação pedagógica preliminar gerada por inteligência artificial. "
        "Não constitui nota oficial do INEP ou correção humana definitiva."
    )
