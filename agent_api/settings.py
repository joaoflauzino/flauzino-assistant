from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GOOGLE_API_KEY: str | None = None
    MODEL_NAME: str = "gemini-2.5-flash"
    FINANCE_SERVICE_URL: str = "http://localhost:8000"
    DATABASE_URL: str


settings = AgentApiSettings()
