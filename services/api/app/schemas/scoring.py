from pydantic import BaseModel, Field


class AreaScoreResponse(BaseModel):
    area: str
    raw_correct: int
    answered_items: int
    parameterized_items: int
    coverage: float
    theta_eap: float
    posterior_sd: float
    score_estimated: float
    credible_interval_95: tuple[float, float]
    method: str = "3PL_EAP"
    calibration_id: str
    model_version: str
    official: bool = False


class AttemptScoreResponse(BaseModel):
    attempt_id: str
    status: str = "completed"
    areas: list[AreaScoreResponse]
    warnings: list[str] = Field(
        default_factory=lambda: [
            "Estimativa independente e não oficial do INEP. "
            "A metodologia considera características dos itens e padrão de respostas, "
            "mas não reproduz garantidamente a escala oficial do INEP."
        ]
    )
