from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    auth0_domain: str
    auth0_client_id: str
    auth0_client_secret: str
    auth0_audience: str

    auth0_callback_url: str
    auth0_logout_url: str

    auth0_google_connection: str = "google-oauth2"
    auth0_microsoft_connection: str = "azuread"

    user_service_url: str = "http://localhost:8002"
    tenant_service_url: str = "http://localhost:8003"

    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()