from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "clinical"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    readonly_user: str = "readonly"
    readonly_password: str = ""

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5-coder:7b"

    max_rows: int = 100

    def dsn(self, readonly: bool = True) -> str:
        user = self.readonly_user if readonly else self.postgres_user
        password = self.readonly_password if readonly else self.postgres_password
        return (
            f"host={self.postgres_host} port={self.postgres_port} "
            f"dbname={self.postgres_db} user={user} password={password}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
