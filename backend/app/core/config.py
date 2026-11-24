from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Medical Diagnostics Support API"
    environment: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    # JSON list, e.g. CORS_ORIGINS='["http://localhost:5173"]'
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    # OpenAI
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    llm_temperature: float = 0.2

    # Vector store / retrieval
    vector_db_path: Path = Path("vector_db")
    collection_name: str = "medical_documents"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4
    max_upload_mb: int = 20

    # Optional S3 archival of uploaded files. Leave bucket empty to disable.
    # Legacy names from the original Flask app (AWS_ACCESS_KEY, ...) are still accepted.
    aws_access_key_id: str | None = Field(
        default=None, validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "AWS_ACCESS_KEY")
    )
    aws_secret_access_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "AWS_SECRET_KEY")
    )
    aws_region: str | None = Field(
        default=None, validation_alias=AliasChoices("AWS_REGION", "AWS_DEFAULT_REGION")
    )
    s3_bucket_name: str | None = Field(
        default=None, validation_alias=AliasChoices("S3_BUCKET_NAME", "AWS_BUCKET_NAME")
    )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
