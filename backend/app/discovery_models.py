from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel

from app.models import timestamp


class Source(BaseModel):
    title: str
    url: str


class Citation(BaseModel):
    text: str
    sources: list[int]


class ResearchBrief(BaseModel):
    text: str
    visual_details: str = ""
    sources: list[Source]
    citations: list[Citation]
    suggestions_html: str = ""
    kind: str = "source_extracts"


class ResearchSnapshot(SQLModel, table=True):
    __tablename__ = "research_snapshots"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    provider: str
    payload: str
    created_at: str = Field(default_factory=timestamp)


class ReferenceCandidate(SQLModel, table=True):
    __tablename__ = "reference_candidates"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    title: str
    source_url: str
    page_url: str
    thumb_url: str
    attribution: str = ""
    license: str = ""
    created_at: str = Field(default_factory=timestamp)


class ReferenceImage(SQLModel, table=True):
    __tablename__ = "reference_images"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    digest: str
    title: str
    source_url: str = ""
    page_url: str = ""
    attribution: str = ""
    license: str = "User supplied; rights not verified"
    width: int
    height: int
    selected: bool = False
    removed: bool = False
    created_at: str = Field(default_factory=timestamp)


class SearchInput(BaseModel):
    query: str = PydanticField(default="", max_length=200)


class SelectionInput(BaseModel):
    selected: bool
