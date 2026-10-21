import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import httpx
from PIL import Image
from sqlmodel import Session, select

from app.delivery_models import Delivery, MetricSample
from app.delivery_service import recover
from app.post_models import PostDraft
from app.routers import publishing
from tests.test_posts import approved, edit_payload


def prepared(client, monkeypatch):
    path, art, post = approved(client)
    with Session(client.app.state.engine) as db:
        row = db.get(PostDraft, post["id"])
        row.platform = "facebook"
        db.add(row)
        db.commit()

    async def identity(*args):
        return {"account_id": "123", "name": "Studio"}

    monkeypatch.setattr(publishing, "verify_identity", identity)
    client.app.state.config.publish_enabled = True
    return path, art, post


def payload(post):
    return {"revision": post["revision"], "account_id": "123", "confirmed": True}


def test_publish_is_gated_and_requires_explicit_current_account(client, monkeypatch):
    path, _, post = prepared(client, monkeypatch)
    url = path + f"/posts/{post['id']}/publish"
    client.app.state.config.publish_enabled = False
    assert client.post(url, json=payload(post)).status_code == 409
    client.app.state.config.publish_enabled = True
    assert client.post(url, json=payload(post) | {"confirmed": False}).status_code == 422
    assert client.post(url, json=payload(post) | {"account_id": "456"}).status_code == 409
    assert client.post(url, json=payload(post) | {"revision": 1}).status_code == 409
    assert client.get(path + "/posts/deliveries").json() == []


def test_publish_records_result_deadlines_and_blocks_duplicate_versions(client, monkeypatch):
    path, _, post = prepared(client, monkeypatch)
    calls = []

    async def publish(config, delivery, content, jpeg, public_url, save):
        assert jpeg.startswith(b"\xff\xd8") and content["alt_text"] == post["alt_text"]
        save("444")
        calls.append(delivery.id)
        return "123_999"

    monkeypatch.setattr(publishing.social, "publish", publish)
    response = client.post(path + f"/posts/{post['id']}/publish", json=payload(post))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "published"
    rows = client.get(path + "/posts/deliveries").json()
    assert len(rows) == 1 and rows[0]["container_id"] == "444"
    assert [s["window"] for s in rows[0]["samples"]] == ["1h", "24h", "7d"]
    assert all(s["status"] == "pending" and s["values"] == {} for s in rows[0]["samples"])
    assert client.post(path + f"/posts/{post['id']}/publish", json=payload(post)).status_code == 409
    saved = client.get(path + "/posts").json()[0]
    assert saved["publication_method"] == "connected"
    new = client.post(
        path + f"/posts/{post['id']}/versions",
        json=edit_payload(saved, alt_text="Updated accessibility description"),
    ).json()
    new = client.post(
        path + f"/posts/{new['id']}/approve", json={"revision": 1, "content_reviewed": True}
    ).json()
    assert client.post(path + f"/posts/{new['id']}/publish", json=payload(new)).status_code == 409
    assert len(calls) == 1


def test_uncertain_request_is_not_resent_and_reconciles_only_matching_author_and_text(
    client, monkeypatch
):
    path, _, post = prepared(client, monkeypatch)

    async def fail(*args):
        raise httpx.ReadTimeout("private-token must not leak")

    monkeypatch.setattr(publishing.social, "publish", fail)
    response = client.post(path + f"/posts/{post['id']}/publish", json=payload(post))
    assert response.json()["status"] == "uncertain" and "private-token" not in response.text
    assert client.post(path + f"/posts/{post['id']}/publish", json=payload(post)).status_code == 409

    async def remote(*args):
        return {"id": "123_999", "owner": "wrong", "text": post["post_text"]}

    monkeypatch.setattr(publishing.social, "read_post", remote)
    url = path + f"/posts/{post['id']}/reconcile"
    assert client.post(url, json={"remote_id": "123_999"}).status_code == 409

    async def remote_ok(*args):
        return {"id": "123_999", "owner": "123", "text": post["post_text"]}

    monkeypatch.setattr(publishing.social, "read_post", remote_ok)
    assert client.post(url, json={"remote_id": "123_999"}).status_code == 200
    assert client.post(url, json={"remote_id": "123_999"}).status_code == 409
    assert len(client.get(path + "/posts/deliveries").json()[0]["samples"]) == 3


def test_concurrent_publish_sends_once_and_daily_cap_counts_uncertain_results(client, monkeypatch):
    path, _, post = prepared(client, monkeypatch)
    calls = []

    async def fail(*args):
        calls.append(1)
        await asyncio.sleep(0.05)
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(publishing.social, "publish", fail)
    url = path + f"/posts/{post['id']}/publish"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: client.post(url, json=payload(post)).status_code, range(2))
        )
    assert sorted(results) == [200, 409] and len(calls) == 1
    client.app.state.config.daily_post_cap = 1
    path2, _, post2 = prepared(client, monkeypatch)
    with Session(client.app.state.engine) as db:
        row = db.get(PostDraft, post2["id"])
        row.caption += " Different caption."
        db.add(row)
        db.commit()
    response = client.post(path2 + f"/posts/{post2['id']}/publish", json=payload(post2))
    assert response.status_code == 409 and "cap" in response.text
    assert len(calls) == 1


def test_startup_recovers_writes_as_uncertain_and_reads_as_pending(client, monkeypatch):
    path, _, post = prepared(client, monkeypatch)
    with Session(client.app.state.engine) as db:
        row = Delivery(
            project_id=path.split("/")[-1],
            post_id=post["id"],
            platform="facebook",
            account_id="123",
            account_name="Studio",
            fingerprint="test",
            content_json="{}",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        db.add(
            MetricSample(
                delivery_id=row.id,
                window="1h",
                due_at="2020-01-01T00:00:00+00:00",
                status="running",
            )
        )
        db.commit()
    recover(client.app.state.engine)
    with Session(client.app.state.engine) as db:
        assert db.exec(select(Delivery)).one().status == "uncertain"
        assert db.exec(select(MetricSample)).one().status == "pending"
        assert db.get(PostDraft, post["id"]).status == "uncertain"


def test_hosted_image_and_instagram_dimensions_are_checked_before_side_effects(client, monkeypatch):
    path, _, post = prepared(client, monkeypatch)
    with Session(client.app.state.engine) as db:
        row = db.get(PostDraft, post["id"])
        row.platform = "instagram"
        db.add(row)
        db.commit()
    monkeypatch.setattr(publishing, "download_image", lambda _: b"different image")
    response = client.post(
        path + f"/posts/{post['id']}/publish",
        json=payload(post) | {"public_image_url": "https://example.com/art.jpg"},
    )
    assert response.status_code == 409 and "aspect" in response.text
    assert client.get(path + "/posts/deliveries").json() == []


def test_hosted_bytes_must_match_the_exact_downloaded_jpeg(client, monkeypatch):
    image = BytesIO()
    Image.new("RGB", (400, 500), "brown").save(image, "PNG")
    monkeypatch.setattr("tests.test_posts.pixels", lambda: image.getvalue())
    path, _, post = prepared(client, monkeypatch)
    with Session(client.app.state.engine) as db:
        row = db.get(PostDraft, post["id"])
        row.platform = "instagram"
        db.add(row)
        db.commit()
    endpoint = path + f"/posts/{post['id']}"
    jpeg = client.get(endpoint + "/publish-image").content
    assert jpeg.startswith(b"\xff\xd8")
    monkeypatch.setattr(publishing, "download_image", lambda _: b"different")
    body = payload(post) | {"public_image_url": "https://example.com/art.jpg"}
    assert client.post(endpoint + "/publish", json=body).status_code == 422
    assert client.get(path + "/posts/deliveries").json() == []
    monkeypatch.setattr(publishing, "download_image", lambda _: jpeg)

    async def send(config, delivery, content, uploaded, url, save):
        assert uploaded == jpeg and url == body["public_image_url"]
        return "789"

    monkeypatch.setattr(publishing.social, "publish", send)
    assert client.post(endpoint + "/publish", json=body).json()["status"] == "published"
