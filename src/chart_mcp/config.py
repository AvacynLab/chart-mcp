"""Configuration module loading environment variables via Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, List, cast

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    api_token: str = Field(..., alias="API_TOKEN", min_length=8)
    exchange: str = Field("binance", alias="EXCHANGE")
    allowed_origins: List[str] = Field(default_factory=list, alias="ALLOWED_ORIGINS")
    llm_provider: str = Field("stub", alias="LLM_PROVIDER")
    llm_model: str = Field("heuristic-v1", alias="LLM_MODEL")
    stream_heartbeat_ms: int = Field(5000, alias="STREAM_HEARTBEAT_MS", ge=1000, le=60000)
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    rate_limit_per_minute: int = Field(60, alias="RATE_LIMIT_PER_MINUTE", ge=1)
    feature_finance: bool = Field(
        True,
        alias="FEATURE_FINANCE",
        description=(
            "Toggle finance-specific services and routes. This allows the backend to"
            " expose only core market capabilities when the feature flag is disabled."
        ),
    )
    playwright_mode: bool = Field(
        False,
        alias="PLAYWRIGHT",
        description="Enable relaxed safeguards for deterministic Playwright runs.",
    )

    @validator("allowed_origins", pre=True)
    def _split_origins(cls, value: List[str] | str) -> List[str]:
        if isinstance(value, str):
            # Accept comma-separated origins for ergonomic environment configuration.
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    class Config:
        """Pydantic settings metadata for environment loading."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        validate_by_name = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()  # type: ignore[call-arg]


class _SettingsProxy:
    """Proxy deferring ``Settings`` instantiation until attributes are accessed."""

    __slots__ = ()

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow tests to monkeypatch settings without forcing global rewrites."""

        # ``monkeypatch.setattr`` relies on being able to assign attributes directly on
        # the proxy returned from the configuration module.  By forwarding the
        # assignment to the lazily-instantiated ``Settings`` object we keep imports
        # lightweight (the proxy itself remains empty) while still supporting test
        # overrides such as tweaking ``stream_heartbeat_ms`` for deterministic SSE
        # assertions.
        setattr(get_settings(), name, value)


settings = cast(Settings, _SettingsProxy())
