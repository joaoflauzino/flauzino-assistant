from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    TELEGRAM_BOT_TOKEN: str
    AGENT_API_URL: str = "http://localhost:8001"
    DATABASE_URL: str
    REQUEST_TIMEOUT: int = 30


settings = TelegramApiSettings()
