import logging
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    SUPABASE_URL: str
    SUPABASE_KEY: str
    BINANCE_API_KEY: str
    BINANCE_API_SECRET: str
    USE_TESTNET: bool = True
    BINANCE_PROXY: Optional[str] = None

    @field_validator("BINANCE_API_KEY", "BINANCE_API_SECRET", "SUPABASE_KEY")
    @classmethod
    def strip_values(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    LOG_LEVEL: int = logging.INFO
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%d/%m/%Y %H:%M:%S"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def setup_logging():

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(), logging.FileHandler("app.log", mode="a")],
    )


settings = Settings()
