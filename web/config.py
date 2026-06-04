"""Web app settings loaded from env vars / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BRAND3_",
        extra="ignore",
    )

    # Rate limit
    rate_limit_enabled: bool = True
    rate_limit_per_ip: int = 5
    rate_limit_window_hours: int = 24
    rate_limit_bypass_ips: str = ""

    # Team access
    team_token: str = ""
    cookie_secret: str = ""

    # Scanner API access
    scanner_api_token: str = ""

    # Queue
    max_concurrent_analyses: int = 2
    analysis_timeout_seconds: int = 600

    # Deployment
    base_url: str = "http://localhost:8000"
    environment: str = "development"  # development | production


def get_settings() -> Settings:
    s = Settings()
    if s.environment == "production":
        missing: list[str] = []
        if not s.team_token:
            missing.append("BRAND3_TEAM_TOKEN")
        if not s.cookie_secret or len(s.cookie_secret) < 32:
            missing.append("BRAND3_COOKIE_SECRET (min 32 chars)")
        if not s.scanner_api_token or len(s.scanner_api_token) < 24:
            missing.append("BRAND3_SCANNER_API_TOKEN (min 24 chars)")
        if missing:
            raise RuntimeError(
                "production environment missing secrets: " + ", ".join(missing)
            )
    return s


settings = get_settings()
