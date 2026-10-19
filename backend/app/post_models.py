from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import Field as InputField
from sqlmodel import Field, SQLModel

from app.models import timestamp


class PostDraft(SQLModel, table=True):
    __tablename__ = "post_drafts"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    artwork_id: str = Field(foreign_key="artwork.id")
    artwork_revision: int
    version: int
    platform: str
    tone: str
    caption: str
    hashtags_json: str
    alt_text: str = ""
    disclosure: str = "AI-assisted fan artwork. Unofficial interpretation."
    context_json: str
    provider: str
    status: str = "draft"
    revision: int = 1
    approved_at: str = ""
    publication_url: str = ""
    published_at: str = ""
    created_at: str = Field(default_factory=timestamp)


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artwork_id: str
    platform: Literal["instagram", "facebook"] = "instagram"
    tone: Literal["reflective", "playful", "minimal"] = "reflective"
    provider: Literal["local", "gemini"] = "local"


class PostEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = InputField(ge=1)
    caption: str = InputField(min_length=1, max_length=5000)
    hashtags: list[str] = InputField(max_length=20)
    alt_text: str = InputField(max_length=1000)
    disclosure: str = InputField(min_length=1, max_length=300)

    @field_validator("caption", "disclosure")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Caption and disclosure cannot be blank.")
        return value.strip()

    @field_validator("hashtags")
    @classmethod
    def tags(cls, values):
        result = []
        for value in values:
            tag = value.strip().removeprefix("#")
            if not tag or len(tag) > 64 or not all(c.isalnum() or c == "_" for c in tag):
                raise ValueError(
                    "Use hashtags with letters, numbers or underscores, up to 64 characters."
                )
            if tag.casefold() not in [t.casefold() for t in result]:
                result.append(tag)
        return result


class ApprovePost(BaseModel):
    revision: int = InputField(ge=1)
    content_reviewed: Literal[True]


class PublicationRecord(BaseModel):
    revision: int = InputField(ge=1)
    url: str = InputField(max_length=2000)
    published_at: str
    manually_published: Literal[True]
