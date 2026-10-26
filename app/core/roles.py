
from pydantic_settings import BaseSettings, SettingsConfigDict


class RoleConfig(BaseSettings):
    EMPLOYEE_ROLE_ID: int = 1
    NODAL_ROLE_ID: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )


role_config = RoleConfig()
