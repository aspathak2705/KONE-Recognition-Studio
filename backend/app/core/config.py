from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "KONE Recognition Studio"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    EXCEL_UPLOADS_DIR: Path = STORAGE_DIR / "uploads" / "excel"
    TEMPLATE_UPLOADS_DIR: Path = STORAGE_DIR / "uploads" / "templates"
    GENERATED_OUTPUTS_DIR: Path = STORAGE_DIR / "generated"

    MAX_UPLOAD_SIZE_MB: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
