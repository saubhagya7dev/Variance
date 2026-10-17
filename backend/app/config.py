from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = f"sqlite:///{(ROOT / 'data' / 'studio.sqlite3').as_posix()}"
    publish_enabled: bool = False
    daily_post_cap: int = 3
    gemini_api_key: str = ""
    brave_api_key: str = ""
    research_provider: Literal["wikipedia", "gemini"] = "wikipedia"
    gemini_model: str = Field(default="gemini-2.5-flash", pattern=r"^[a-zA-Z0-9.-]+$")
    asset_dir: Path = ROOT / "data" / "references"


settings = Settings()
