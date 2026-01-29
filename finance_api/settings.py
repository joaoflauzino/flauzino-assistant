from pydantic_settings import BaseSettings


class FinanceApiSettings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+asyncpg://flauzino:password@localhost:5432/assistant"
    )
    API_BASE_URL: str = "http://localhost:8001"


settings = FinanceApiSettings()
