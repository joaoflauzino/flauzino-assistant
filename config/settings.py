from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_API_KEY: str | None = None
    MODEL_NAME: str = "gemini-2.5-flash"
    DATABASE_URL: str = (
        "postgresql+asyncpg://flauzino:password@localhost:5432/assistant"
    )
    API_BASE_URL: str = "http://localhost:8000"


settings = Settings()
