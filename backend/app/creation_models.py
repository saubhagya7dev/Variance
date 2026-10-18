from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import Field as InputField
from sqlmodel import Field, SQLModel

from app.models import timestamp


class Direction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    style: str = InputField(default="Custom", min_length=1, max_length=100)
    medium: str = InputField(default="Digital illustration", max_length=200)
    mood: str = InputField(default="", max_length=500)
    palette: str = InputField(default="", max_length=500)
    lighting: str = InputField(default="", max_length=500)
    composition: str = InputField(default="", max_length=1000)
    preserve: str = InputField(default="", max_length=2000)
    avoid: str = InputField(default="", max_length=1000)
    aspect_ratio: Literal["1:1", "4:5", "3:2", "16:9", "9:16"] = "4:5"

    @field_validator("style")
    @classmethod
    def nonempty(cls, value: str):
        if not value.strip():
            raise ValueError("Choose or describe a style.")
        return value.strip()


class PromptSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: Direction
    context_hash: str = InputField(pattern=r"^[a-f0-9]{64}$")
    prompt_text: str = InputField(min_length=10, max_length=24000)

    @field_validator("prompt_text")
    @classmethod
    def meaningful(cls, value: str):
        if len(value.strip()) < 10:
            raise ValueError("Enter a prompt of at least 10 nonblank characters.")
        return value.strip()


class PromptVersion(SQLModel, table=True):
    __tablename__ = "prompt_versions"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    version: int
    direction_json: str
    context_json: str
    prompt_text: str
    created_at: str = Field(default_factory=timestamp)


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt_id: str
    mode: Literal["manual", "api"] = "manual"
    target_count: int = InputField(default=4, ge=1, le=4)
    request_key: str = InputField(pattern=r"^[a-f0-9-]{32,36}$")


class CreationBatch(SQLModel, table=True):
    __tablename__ = "creation_batches"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    prompt_id: str = Field(foreign_key="prompt_versions.id")
    mode: str = "manual"
    status: str = "awaiting_import"
    error: str = ""
    target_count: int = 4
    request_key: str
    created_at: str = Field(default_factory=timestamp)
    updated_at: str = Field(default_factory=timestamp)


class Artwork(SQLModel, table=True):
    __tablename__ = "artwork"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    batch_id: str = Field(foreign_key="creation_batches.id")
    digest: str
    title: str
    width: int
    height: int
    decision: str = "pending"
    review_note: str = ""
    revision: int = 1
    created_at: str = Field(default_factory=timestamp)


class ArtworkReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["pending", "approved", "rejected"]
    review_note: str = InputField(default="", max_length=2000)
    revision: int = InputField(ge=1)
