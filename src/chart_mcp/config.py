"""Application configuration powered by Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    # NOTE: provide a permissive default token so import-time configuration does not
    # fail inside CI smoke tests. Real deployments are expected to override this
    # value through the API_TOKEN environment variable.
    api_token: str = Field(
        "dev-token",
        alias="API_TOKEN",
        min_length=8,
        description="Shared bearer token required to access protected endpoints.",
    )
    exchange: str = Field("binance", alias="EXCHANGE")
    allowed_origins: List[str] = Field(default_factory=list, alias="ALLOWED_ORIGINS")
    llm_provider: str = Field("stub", alias="LLM_PROVIDER")
    llm_model: str = Field("heuristic-v1", alias="LLM_MODEL")
    stream_heartbeat_ms: int = Field(5000, alias="STREAM_HEARTBEAT_MS", ge=1000, le=60000)
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    rate_limit_per_minute: int = Field(60, alias="RATE_LIMIT_PER_MINUTE", ge=1)
    feature_finance: bool = Field(True, alias="FEATURE_FINANCE")
    playwright_mode: bool = Field(False, alias="PLAYWRIGHT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_by_name=True,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value: List[str] | str) -> List[str]:
        """Accept comma-separated strings for convenience."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
