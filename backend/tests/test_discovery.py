from io import BytesIO

import pytest
from PIL import Image
from sqlmodel import Session, select

from app import image_store
from app.discovery_models import Citation, ReferenceCandidate, ResearchBrief, Source
from app.models import ProviderCall
from app.providers import discovery as providers
from app.routers import discovery
from tests.test_characters import create


def png():
    output = BytesIO()
    Image.new("RGB", (32, 24), "brown").save(output, "PNG")
    return output.getvalue()


def test_research_persists_evidence_and_failed_refresh_keeps_previous(client, monkeypatch):
    project = create(client)
    path = f"/api/characters/{project['id']}/research"

    async def research(identity):
        assert identity["variant"] == "Original design"
        return ResearchBrief(
            text="Sourced excerpt",
            sources=[Source(title="Fixture", url="https://example.org/source")],
            citations=[Citation(text="Sourced excerpt", sources=[0])],
        )

    monkeypatch.setattr(discovery, "wikipedia_research", research)
    assert client.post(path).status_code == 200
    assert client.get(path).json()[0]["brief"]["citations"][0]["sources"] == [0]

    async def fail(_):
        raise ValueError("No usable evidence")

    monkeypatch.setattr(discovery, "wikipedia_research", fail)
    assert client.post(path).status_code == 422
    assert len(client.get(path).json()) == 1
    assert not client.app.state.discovery_busy
    with Session(client.app.state.engine) as db:
        assert [row.outcome for row in db.exec(select(ProviderCall)).all()] == [
            "success",
            "invalid_result",
        ]


def test_upload_deduplicates_selects_removes_and_enforces_ownership(client):
    first, second = create(client), create(client)
    path = f"/api/characters/{first['id']}/references"
    response = client.post(path + "/upload?title=Reference", content=png())
    assert response.status_code == 200
    ref = response.json()
    assert (ref["width"], ref["height"]) == (32, 24)
    assert client.post(path + "/upload", content=png()).json()["id"] == ref["id"]
    assert len(client.get(path).json()) == 1
    assert client.patch(path + "/" + ref["id"], json={"selected": True}).json()["selected"]
    image = client.get(path + "/" + ref["id"] + "/image")
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    assert (
        client.get(f"/api/characters/{second['id']}/references/{ref['id']}/image").status_code
        == 404
    )
    assert client.delete(path + "/" + ref["id"]).status_code == 200
    assert client.get(path).json() == []
    assert client.post(path + "/upload", content=png()).json()["id"] == ref["id"]


def test_upload_rejects_html_oversize_and_archived_project(client):
    project = create(client)
    path = f"/api/characters/{project['id']}"
    assert (
        client.post(path + "/references/upload", content=b"<svg onload='alert(1)'/>").status_code
        == 422
    )
    assert (
        client.post(
            path + "/references/upload", content=b"x" * (image_store.MAX_BYTES + 1)
        ).status_code
        == 413
    )
    client.post(path + "/archive", json={"revision": 1, "archived": True})
    assert client.post(path + "/references/upload", content=png()).status_code == 409
    assert client.post(path + "/research").status_code == 409


def test_missing_gemini_key_and_duplicate_inflight(client):
    project = create(client)
    client.app.state.config.research_provider = "gemini"
    client.app.state.config.gemini_api_key = ""
    path = f"/api/characters/{project['id']}/research"
    assert client.post(path).status_code == 503
    client.app.state.discovery_busy.add(project["id"])
    assert client.post(path).status_code == 409


def test_search_import_keeps_attribution(client, monkeypatch):
    project = create(client)
    path = f"/api/characters/{project['id']}"

    async def search(project_id, query):
        assert query == "Fixture art"
        return [
            ReferenceCandidate(
                project_id=project_id,
                title="Original art",
                source_url="https://example.org/a.png",
                thumb_url="https://example.org/t.png",
                page_url="https://example.org/page",
                attribution="Artist",
                license="CC BY 4.0",
            )
        ]

    monkeypatch.setattr(discovery, "commons_search", search)
    monkeypatch.setattr(discovery, "download_image", lambda _: png())
    result = client.post(path + "/candidates", json={"query": "Fixture art"}).json()[0]
    assert client.get(path + f"/candidates/{result['id']}/thumbnail").status_code == 200
    imported = client.post(path + f"/candidates/{result['id']}/import").json()
    assert imported["attribution"] == "Artist" and imported["license"] == "CC BY 4.0"


def test_gemini_requires_real_grounding_links_and_ignores_invalid_chunks():
    candidate = {
        "finishReason": "STOP",
        "content": {"parts": [{"text": "OVERVIEW\nA hero.\nVISUAL DNA\nBrown coat."}]},
        "groundingMetadata": {
            "groundingChunks": [
                {"web": {"uri": "javascript:alert(1)"}},
                {"web": {"uri": "https://example.org", "title": "Official"}},
            ],
            "groundingSupports": [
                {"segment": {"text": "Brown coat."}, "groundingChunkIndices": [1, 99]}
            ],
        },
    }
    parsed = providers.parse_gemini({"candidates": [candidate]})
    assert parsed.visual_details == "Brown coat."
    assert parsed.citations[0].sources == [0]
    candidate["groundingMetadata"]["groundingSupports"] = []
    with pytest.raises(ValueError, match="evidence"):
        providers.parse_gemini({"candidates": [candidate]})


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "192.168.1.1"],
)
def test_download_blocks_private_dns(monkeypatch, address):
    monkeypatch.setattr(
        image_store.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", (address, 443))]
    )
    with pytest.raises(ValueError, match="public"):
        image_store.download_image("https://example.org/a.png")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/a",
        "file:///etc/passwd",
        "https://user:pass@example.org/a",
        "https://example.org:8080/a",
    ],
)
def test_download_rejects_unsafe_url_shapes(url):
    with pytest.raises(ValueError):
        image_store.download_image(url)


def test_redirect_destination_revalidated(monkeypatch):
    monkeypatch.setattr(
        image_store,
        "public_addresses",
        lambda host: (
            ["93.184.216.34"]
            if host == "example.org"
            else (_ for _ in ()).throw(ValueError("private target"))
        ),
    )

    class Connection:
        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def close(self):
            pass

        def getresponse(self):
            return self

        status = 302

        def getheader(self, name):
            return "https://127.0.0.1/private"

    monkeypatch.setattr(image_store, "PinnedHTTPSConnection", Connection)
    with pytest.raises(ValueError, match="private"):
        image_store.download_image("https://example.org/image")


def test_normalization_removes_metadata_and_limits_dimensions():
    from PIL.PngImagePlugin import PngInfo

    metadata = PngInfo()
    metadata.add_text("private", "do not persist")
    out = BytesIO()
    Image.new("RGB", (4500, 2), "brown").save(out, "PNG", pnginfo=metadata)
    clean, width, _ = image_store.normalize_image(out.getvalue())
    assert width == 4096
    assert "private" not in Image.open(BytesIO(clean)).info
