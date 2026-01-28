from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_API_KEY: str | None = None
    MODEL_NAME: str = "gemini-2.5-flash"


settings = Settings()
