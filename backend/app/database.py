
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)
    REFRESH_COOKIE_SECURE: bool = False
    REFRESH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    PASSWORD_RESET_DELIVERY_MODE: str = "disabled"
    PASSWORD_RESET_FRONTEND_URL: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = Field(default=587, gt=0, le=65535)
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_STARTTLS: bool = True
    APP_ENV: str = "development"
    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    REDIS_URL: str | None = None
    DASHBOARD_CACHE_TTL_SECONDS: int = Field(default=60, gt=0, le=86400)
    RATE_LIMIT_REDIS_URL: str | None = None
    LOGIN_RATE_LIMIT_REQUESTS: int = Field(default=5, gt=0)
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)
    FORGOT_PASSWORD_RATE_LIMIT_REQUESTS: int = Field(default=5, gt=0)
    FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=3600,
        gt=0,
    )
    RESET_PASSWORD_RATE_LIMIT_REQUESTS: int = Field(default=5, gt=0)
    RESET_PASSWORD_RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=900,
        gt=0,
    )

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        if "*" in {origin.strip() for origin in value.split(",")}:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must not contain a wildcard"
            )
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.APP_ENV.lower() == "production":
            if not self.RATE_LIMIT_REDIS_URL:
                raise ValueError(
                    "RATE_LIMIT_REDIS_URL is required in production"
                )
            if "CORS_ALLOWED_ORIGINS" not in self.model_fields_set:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must be set in production"
                )
            if not self.REFRESH_COOKIE_SECURE:
                raise ValueError(
                    "REFRESH_COOKIE_SECURE must be enabled in production"
                )
        if (
            self.REFRESH_COOKIE_SAMESITE == "none"
            and not self.REFRESH_COOKIE_SECURE
        ):
            raise ValueError(
                "REFRESH_COOKIE_SECURE must be enabled for SameSite=None"
            )
        return self

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
