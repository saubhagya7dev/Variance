from pathlib import Path

from app.providers.base import GeneratedImage, ImageHit, PublishResult, ResearchResult


class FakeLLM:
    name = "fixture-only"

    async def research(self, query: str) -> ResearchResult:
        return ResearchResult(
            summary="Test fixture only", visual_spec={}, evidence=[], grounded=False
        )

    async def generate_text(self, prompt: str, *, json_schema: dict | None = None) -> str:
        return '{"fixture": true}'


class FakeSearch:
    async def image_search(self, query: str, *, limit: int = 30) -> list[ImageHit]:
        return []


class FakeImages:
    supports_references = True

    async def generate(
        self, prompt: str, *, references: list[Path], n: int = 4
    ) -> list[GeneratedImage]:
        return []


class FakePublisher:
    async def publish(self, payload: dict, *, dry_run: bool = True) -> PublishResult:
        return PublishResult(status="dry_run" if dry_run else "fixture_only")


class FakeMetrics:
    async def fetch(self, external_id: str) -> dict[str, float | None]:
        return {"views": None}
