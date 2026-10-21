import hashlib
import json
import sqlite3
from io import BytesIO
from zipfile import ZipFile

import pytest

from app.backup import create_backup, restore
from tests.test_posts import approved


def test_backup_roundtrip_preserves_database_and_images_and_excludes_env(client, tmp_path):
    path, art, post = approved(client)
    (client.app.state.config.asset_dir / ".env").write_text("SECRET=do-not-back-up")
    create_backup(
        client.app.state.engine, client.app.state.config.asset_dir, tmp_path / "direct.zip"
    )
    response = client.post("/api/operations/backup")
    assert response.status_code == 200, response.text
    archive = tmp_path / "backup.zip"
    archive.write_bytes(response.content)
    destination = tmp_path / "restored"
    restore(archive, destination)
    with ZipFile(archive) as pack:
        assert all(".env" not in name for name in pack.namelist())
    with sqlite3.connect(destination / "studio.sqlite3") as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            db.execute("SELECT caption FROM post_drafts WHERE id=?", (post["id"],)).fetchone()[0]
            == post["caption"]
        )
    original = client.app.state.config.asset_dir / "artwork" / f"{art['digest']}.png"
    assert (
        destination / "assets" / "artwork" / original.name
    ).read_bytes() == original.read_bytes()
    with pytest.raises(ValueError, match="empty"):
        restore(archive, destination)
    assert client.get(path + "/posts").status_code == 200


@pytest.mark.parametrize(
    "name",
    [
        "../outside",
        "assets/../../outside",
        "C:/outside",
        "assets\\outside",
        "assets/CON",
        "assets/a/../b",
        "assets/file.png:stream",
    ],
)
def test_restore_rejects_unsafe_paths_before_writing(tmp_path, name):
    output = BytesIO()
    with ZipFile(output, "w") as pack:
        pack.writestr(name, b"test")
        pack.writestr(
            "manifest.json",
            json.dumps({"version": 1, "files": {name: hashlib.sha256(b"test").hexdigest()}}),
        )
    output.seek(0)
    with pytest.raises(ValueError):
        restore(output, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_restore_rejects_corruption_before_writing_and_backup_requires_local_header(
    client, tmp_path
):
    approved(client)
    response = client.post("/api/operations/backup")
    output = BytesIO()
    with ZipFile(BytesIO(response.content)) as source, ZipFile(output, "w") as target:
        for name in source.namelist():
            target.writestr(name, b"damaged" if name == "studio.sqlite3" else source.read(name))
    output.seek(0)
    with pytest.raises(ValueError, match="checksum"):
        restore(output, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
    assert (
        client.post("/api/operations/backup", headers={"X-Variance-Client": ""}).status_code == 403
    )
    assert client.get("/api/operations").json()["database_ok"]
