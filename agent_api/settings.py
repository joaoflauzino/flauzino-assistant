from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str | None = None
    MODEL_NAME: str = "gpt-6-luna"
    FINANCE_SERVICE_URL: str = "http://localhost:8000"
    GRAPH_SERVICE_URL: str = "http://localhost:8002"
    MCP_SERVER_URL: str = "http://localhost:8002"
    DATABASE_URL: str
    DB_ECHO: bool = False


settings = AgentApiSettings()
