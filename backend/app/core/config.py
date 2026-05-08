from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # App
    app_name: str = "StreamVault Analytics Assistant"
    app_env:  str = "development"
    log_level: str = "INFO"

    # AI
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_model:   str = "llama-3.3-70b-versatile"

    # Auth
    secret_key:                    str = Field(..., env="SECRET_KEY")
    algorithm:                     str = "HS256"
    access_token_expire_minutes:   int = 480
    admin_password:                str = Field(..., env="ADMIN_PASSWORD")
    analyst_password:              str = Field(..., env="ANALYST_PASSWORD")

    # Paths
    data_dir:        str = "/app/data"
    sqlite_db_path:  str = "/app/data/sqlite/streamvault.db"
    chroma_db_path:  str = "/app/data/chroma"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def csv_dir(self) -> Path:
        return Path(self.data_dir) / "csv"

    @property
    def pdf_dir(self) -> Path:
        return Path(self.data_dir) / "pdf"

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_db_path}"

    class Config:
        env_file = ".env"
        extra    = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()