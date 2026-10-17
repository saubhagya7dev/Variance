import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'studio.sqlite3'}",
            asset_dir=tmp_path / "images",
            _env_file=None,
        )
    )
    with TestClient(
        app, base_url="http://localhost", headers={"X-Variance-Client": "studio"}
    ) as client:
        yield client
