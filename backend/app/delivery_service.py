"""Durable publication state and scheduled, read-only measurements."""

import asyncio
import json
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlmodel import Session, select

from app.delivery_models import Delivery, MetricSample
from app.models import timestamp
from app.post_models import PostDraft
from app.providers import social
from app.providers.runner import call_provider
from app.routers.connections import verify_identity


def complete(db, delivery, remote_id, url=""):
    delivery.remote_id = social.remote_id(remote_id)
    delivery.status = "published"
    delivery.error = ""
    if delivery.platform == "x":
        url = f"https://x.com/i/status/{delivery.remote_id}"
    elif delivery.platform == "facebook":
        url = f"https://www.facebook.com/{delivery.remote_id}"
    delivery.publication_url = url
    delivery.published_at = timestamp()
    post = db.get(PostDraft, delivery.post_id)
    post.status = "published"
    post.publication_method = "connected"
    post.publication_url = url
    post.published_at = delivery.published_at
    post.revision += 1
    db.add(post)
    db.add(delivery)
    for label, hours in (("1h", 1), ("24h", 24), ("7d", 168)):
        db.add(
            MetricSample(
                delivery_id=delivery.id,
                window=label,
                due_at=(
                    datetime.fromisoformat(delivery.published_at) + timedelta(hours=hours)
                ).isoformat(),
            )
        )


def recover(engine):
    with Session(engine) as db:
        for row in db.exec(select(Delivery).where(Delivery.status == "sending")):
            row.status = "uncertain"
            row.error = (
                "Publication interrupted. Check the destination and reconcile; do not resend."
            )
            post = db.get(PostDraft, row.post_id)
            post.status = "uncertain"
            db.add(post)
            db.add(row)
        for sample in db.exec(select(MetricSample).where(MetricSample.status == "running")):
            sample.status = "pending"
            db.add(sample)
        db.commit()


async def collect_one(state):
    with Session(state.engine) as db:
        db.exec(text("BEGIN IMMEDIATE"))
        sample = db.exec(
            select(MetricSample)
            .where(MetricSample.status == "pending", MetricSample.due_at <= timestamp())
            .order_by(MetricSample.due_at)
        ).first()
        if not sample:
            return False
        sample.status = "running"
        db.add(sample)
        db.commit()
        db.refresh(sample)
        delivery = db.get(Delivery, sample.delivery_id)
        try:
            identity = await verify_identity(delivery.platform, state.config)
            if identity["account_id"] != delivery.account_id:
                raise ValueError("Account changed")
            values = await call_provider(
                state.engine,
                delivery.platform,
                "metrics",
                lambda: social.metrics(state.config, delivery),
                timeout=35,
            )
            values = {
                k: v for k, v in values.items() if isinstance(k, str) and type(v) is int and v >= 0
            }
            if not values:
                raise ValueError("No measurements returned")
            sample.values_json = json.dumps(values)
            sample.status = "collected"
            sample.error = ""
        except Exception:
            sample.status = "unavailable"
            sample.error = (
                "Metrics unavailable. Check account, permissions and API access before retrying."
            )
        sample.collected_at = timestamp()
        db.add(sample)
        db.commit()
        return True


async def worker(state):
    while True:
        if state.config.metrics_enabled:
            try:
                if await collect_one(state):
                    continue
            except Exception:
                # Keep the worker alive; interrupted reads are recovered at restart.
                pass
        await asyncio.sleep(30)
