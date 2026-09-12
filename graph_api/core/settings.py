from pydantic_settings import BaseSettings, SettingsConfigDict


class GraphAPISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = GraphAPISettings()
