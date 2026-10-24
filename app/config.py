from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY_LLM_MODEL_REPLACEMENTS = {
    "gemini-2.5-flash": "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite": "gemini-3.1-flash-lite",
    "gemini-2.0-flash": "gemini-3.1-flash-lite",
}


def resolve_project_path(path: str | Path) -> Path:
    configured_path = Path(path)
    if not configured_path.is_absolute():
        configured_path = PROJECT_ROOT / configured_path
    return configured_path.resolve()


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cricket_connect"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    gemini_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    llm_api_key: str = ""
    llm_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    llm_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    chat_index_dir: str = "data/chat_index"

    @model_validator(mode="before")
    @classmethod
    def normalize_model_entries(cls, values):
        if not isinstance(values, dict):
            return values

        llm_model = values.get("llm_model")
        if isinstance(llm_model, str):
            cleaned_model = llm_model.strip()
            values["llm_model"] = LEGACY_LLM_MODEL_REPLACEMENTS.get(cleaned_model, cleaned_model) or "gemini-3.1-flash-lite"

        embedding_model = values.get("embedding_model")
        if isinstance(embedding_model, str):
            values["embedding_model"] = embedding_model.strip() or "gemini-embedding-001"

        return values

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_gemini_api_key(settings: Settings | None = None) -> str:
    configured = settings or get_settings()
    return configured.gemini_api_key.strip() or configured.llm_api_key.strip()
