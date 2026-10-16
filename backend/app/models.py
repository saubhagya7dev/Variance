from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class CharacterProject(SQLModel, table=True):
    __tablename__ = "character_projects"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    name: str
    franchise: str
    variant: str
    status: str = "entered"
    notes: str = ""
    direction: str = ""
    archived: bool = False
    revision: int = 1
    created_at: str = Field(default_factory=timestamp)
    updated_at: str = Field(default_factory=timestamp)


class ProviderCall(SQLModel, table=True):
    __tablename__ = "provider_calls"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    provider: str
    kind: str
    status_code: int | None = None
    latency_ms: int
    attempt: int
    outcome: str
    created_at: str = Field(default_factory=timestamp)
