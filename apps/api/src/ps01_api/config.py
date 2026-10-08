from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    environment: str = "development"
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 1536
    gemini_chat_model: str = "gemini-3.8-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
