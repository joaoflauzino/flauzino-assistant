from pydantic_settings import BaseSettings, SettingsConfigDict


class FinanceApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    AGENT_SERVICE_URL: str = "http://localhost:8001"
    GRAPH_SERVICE_URL: str = "http://localhost:8002"
    FRONTEND_URL: str = "http://localhost:5173"
    OWN_HOLDER_NAMES: str = "João Lucas Flauzino Cassiano,Lailla Nurrielle Campos Carvalho Flauzino"
    DB_ECHO: bool = False


settings = FinanceApiSettings()
