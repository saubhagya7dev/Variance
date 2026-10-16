from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, HttpUrl


class Evidence(BaseModel):
    claim: str
    source: HttpUrl


class ResearchResult(BaseModel):
    summary: str
    visual_spec: dict[str, str | list[str]]
    evidence: list[Evidence]
    grounded: bool


class ImageHit(BaseModel):
    source_url: HttpUrl
    page_url: HttpUrl
    thumb_url: HttpUrl
    width: int | None = None
    height: int | None = None


class GeneratedImage(BaseModel):
    path: Path
    provider: str
    seed: int | None = None


class PublishResult(BaseModel):
    status: str
    external_id: str | None = None
    url: HttpUrl | None = None


class LLMProvider(Protocol):
    name: str

    async def generate_text(self, prompt: str, *, json_schema: dict | None = None) -> str: ...
    async def research(self, query: str) -> ResearchResult: ...


class SearchProvider(Protocol):
    async def image_search(self, query: str, *, limit: int = 30) -> list[ImageHit]: ...


class ImageProvider(Protocol):
    supports_references: bool

    async def generate(
        self, prompt: str, *, references: list[Path], n: int = 4
    ) -> list[GeneratedImage]: ...


class Publisher(Protocol):
    async def publish(self, payload: dict, *, dry_run: bool = True) -> PublishResult: ...


class MetricsProvider(Protocol):
    async def fetch(self, external_id: str) -> dict[str, float | None]: ...
