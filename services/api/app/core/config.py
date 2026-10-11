from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


PROJECT_ENV = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "ENEM Intelligence"
    API_V1_STR: str = "/v1"
    SECRET_KEY: str = "enem-intelligence-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 dia
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias

    DATABASE_URL: str = "sqlite:///./enem_intelligence.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    OMR_CONFIDENCE_THRESHOLD: float = 0.85
    OMR_IMAGE_UPLOAD_DIR: str = "./uploads"

    # Google Gemini AI Integration (Gratuita via Google AI Studio)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
