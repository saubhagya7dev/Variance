from uuid import uuid4

from sqlmodel import Field, SQLModel

from app.models import timestamp


class Delivery(SQLModel, table=True):
    __tablename__ = "deliveries"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    project_id: str = Field(foreign_key="character_projects.id")
    post_id: str = Field(foreign_key="post_drafts.id", unique=True)
    platform: str
    account_id: str
    account_name: str
    fingerprint: str = Field(unique=True)
    status: str = "sending"
    container_id: str = ""
    remote_id: str = ""
    publication_url: str = ""
    content_json: str
    error: str = ""
    created_at: str = Field(default_factory=timestamp)
    published_at: str = ""


class MetricSample(SQLModel, table=True):
    __tablename__ = "metric_samples"
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    delivery_id: str = Field(foreign_key="deliveries.id")
    window: str
    due_at: str
    status: str = "pending"
    values_json: str = "{}"
    error: str = ""
    collected_at: str = ""
