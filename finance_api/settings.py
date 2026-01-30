from pydantic_settings import BaseSettings, SettingsConfigDict


class FinanceApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    AGENT_SERVICE_URL: str = "http://localhost:8001"


settings = FinanceApiSettings()
