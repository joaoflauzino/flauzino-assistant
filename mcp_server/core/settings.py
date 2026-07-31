from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    FINANCE_SERVICE_URL: str = "http://finance_api:8000"


settings = MCPServerSettings()
