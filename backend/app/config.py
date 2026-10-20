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
    gemini_captions_enabled: bool = False
    brave_api_key: str = ""
    research_provider: Literal["wikipedia", "gemini"] = "wikipedia"
    gemini_model: str = Field(default="gemini-3.8-flash", pattern=r"^[a-zA-Z0-9.-]+$")
    asset_dir: Path = ROOT / "data" / "references"
    gemini_image_model: Literal["gemini-nano-banana-2.1", "gemini-3.1-flash-image"] = (
        "gemini-nano-banana-2.1"
    )
    gemini_image_paid_enabled: bool = False

    @property
    def generation_ready(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_image_paid_enabled)


settings = Settings()
