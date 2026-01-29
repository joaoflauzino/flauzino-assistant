from pydantic_settings import BaseSettings


class AgentApiSettings(BaseSettings):
    GOOGLE_API_KEY: str | None = None
    MODEL_NAME: str = "gemini-2.5-flash"
    API_BASE_URL: str = "http://localhost:8000"


settings = AgentApiSettings()
