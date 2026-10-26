from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Scanned Service Book API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str
    REDIS_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # SCANNED SERVICEBOOK CONFIG
    SCANNED_SB_TENANT_ID: int = 1
    SCANNED_SB_MODULE_ID: int = 1
    SCANNED_SB_WORKFLOW_TEMPLATE_ID: int = 1
    SCANNED_SB_ASSIGNEE_ROLE_ID: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore",)


settings = Settings()
