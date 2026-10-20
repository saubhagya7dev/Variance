from sqlmodel import Session

from app.creation_models import Artwork
from tests.test_posts import approved, ready


def test_preflight_is_local_and_does_not_publish(client):
    path, _, post = approved(client)
    response = client.post(
        path + f"/posts/{post['id']}/preflight", json={"revision": post["revision"]}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["content_ready"] and not result["live_ready"]
    assert result["mode"] == "dry_run" and result["blockers"]
    assert client.get(path + "/posts").json()[0]["status"] == "approved"
    stale = client.post(path + f"/posts/{post['id']}/preflight", json={"revision": 1}).json()
    assert not stale["content_ready"]


def test_preflight_rejects_drafts_changed_art_missing_files_and_wrong_project(client):
    path, art, post = ready(client)
    assert not client.post(
        path + f"/posts/{post['id']}/preflight", json={"revision": post["revision"]}
    ).json()["content_ready"]
    path, art, post = approved(client)
    with Session(client.app.state.engine) as db:
        image = db.get(Artwork, art["id"])
        image.decision = "rejected"
        db.add(image)
        db.commit()
    endpoint = path + f"/posts/{post['id']}/preflight"
    assert not client.post(endpoint, json={"revision": post["revision"]}).json()["content_ready"]
    (client.app.state.config.asset_dir / "artwork" / f"{art['digest']}.png").unlink()
    result = client.post(endpoint, json={"revision": post["revision"]}).json()
    assert not result["checks"][-1]["passed"]
    other, _, _ = ready(client)
    assert (
        client.post(
            other + f"/posts/{post['id']}/preflight", json={"revision": post["revision"]}
        ).status_code
        == 404
    )
