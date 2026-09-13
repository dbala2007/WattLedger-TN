"""Application configuration, loaded from environment variables / .env.

Using pydantic-settings means every value below can be overridden by an
environment variable of the same name (case-insensitive) without touching
code, e.g. setting DATABASE_URL in the shell or in a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # SQLite file used for local development. Kept relative to the backend/
    # folder so the DB file lives alongside the code, not on C:\.
    database_url: str = "sqlite:///./wattledger.db"

    # Standard Python logging level name (DEBUG, INFO, WARNING, ERROR).
    log_level: str = "INFO"

    # Default locale/timezone per CLAUDE.md - used later for date display.
    timezone: str = "Asia/Kolkata"

    # Signs login tokens (JWTs). MUST be overridden via .env - CLAUDE.md
    # forbids hardcoded secrets. The fallback below only exists so a fresh
    # checkout without a .env still starts for local exploration; anyone
    # who sets it in .env invalidates every token signed with the old key
    # (i.e. logs everyone out), which is expected when rotating it.
    secret_key: str = "dev-only-insecure-secret-change-me"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days - single access token, no refresh flow yet.

    # Comma-separated list of allowed browser origins for the web build,
    # e.g. "https://wattledger.example.com,https://www.wattledger.example.com".
    # "*" (the default) is fine for local development, where the Flutter web
    # dev server runs on an unpredictable localhost port, but CLAUDE.md
    # section 14 requires this be restricted to known origins before any
    # real deployment - set CORS_ORIGINS in production's .env.
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# A single shared Settings instance - import this rather than constructing
# Settings() again elsewhere, so the whole app agrees on configuration.
settings = Settings()
