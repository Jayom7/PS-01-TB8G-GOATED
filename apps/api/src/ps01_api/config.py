from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    web_origin: str = "http://localhost:3000"
    supabase_url: str | None = None
    supabase_publishable_key: SecretStr | None = None
    supabase_secret_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    # Optional, explicitly provisioned independent project. No key rotation.
    gemini_project_id: str | None = None
    gemini_secondary_project_id: str | None = None
    gemini_secondary_api_key: SecretStr | None = None
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 1536
    gemini_chat_model: str = "gemini-3.8-flash"
    gemini_fallback_chat_model: str = "gemini-3.7-flash"
    generation_budget_seconds: float = Field(default=45, ge=1, le=60)
    ingestion_enabled: bool = False
    original_storage: Literal["local", "supabase"] = "local"
    ocr_engine: Literal["paddleocr", "tesseract"] = "paddleocr"


@lru_cache
def get_settings() -> Settings:
    return Settings()
