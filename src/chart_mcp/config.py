"""Application configuration powered by Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List, cast

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
    allowed_origins_raw: str = Field(
        "",
        alias="ALLOWED_ORIGINS",
        description="Comma-separated list of origins allowed to access the API.",
    )
    llm_provider: str = Field("stub", alias="LLM_PROVIDER")
    llm_model: str = Field("heuristic-v1", alias="LLM_MODEL")
    stream_heartbeat_ms: int = Field(5000, alias="STREAM_HEARTBEAT_MS", ge=1000, le=60000)
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    rate_limit_per_minute: int = Field(60, alias="RATE_LIMIT_PER_MINUTE", ge=1)
    feature_finance: bool = Field(True, alias="FEATURE_FINANCE")
    playwright_mode: bool = Field(False, alias="PLAYWRIGHT")
    searxng_base_url: str | None = Field(
        None,
        alias="SEARXNG_BASE_URL",
        description="Base URL of the self-hosted SearxNG instance (disable search when empty).",
    )
    searxng_timeout: float = Field(
        10.0,
        alias="SEARXNG_TIMEOUT",
        ge=1.0,
        le=60.0,
        description="Timeout in seconds for SearxNG HTTP calls.",
    )
    ohlc_cache_ttl_seconds: int = Field(
        120,
        alias="OHLC_CACHE_TTL_SECONDS",
        ge=0,
        le=3600,
        description="Amount of time OHLC cache entries remain valid before expiry.",
    )
    ohlc_cache_max_entries: int = Field(
        256,
        alias="OHLC_CACHE_MAX_ENTRIES",
        ge=1,
        le=2048,
        description="Maximum number of OHLC cache entries kept in memory.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_by_name=True,
    )

    @field_validator("api_token", mode="before")
    @classmethod
    def ensure_token_has_value(cls, value: str | None) -> str:
        """Fallback to the default token when an empty string is provided.

        GitHub Actions often forwards environment variables with ``-e NAME=$NAME``.
        When ``$NAME`` is undefined Docker passes an empty string, which Pydantic
        interprets as an explicit value and therefore triggers a validation error
        against the ``min_length`` constraint. This validator normalises such
        cases back to the default development token so the container stays
        bootable while still allowing operators to override it with a real secret.
        """
        default_token = cast(str, cls.model_fields["api_token"].default)
        if value is None or value == "":
            return default_token
        return value

    @property
    def allowed_origins(self) -> List[str]:
        """Return the sanitized CORS origins as a list."""
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    @property
    def searxng_enabled(self) -> bool:
        """Return whether the optional SearxNG integration is configured."""
        return bool(self.searxng_base_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
