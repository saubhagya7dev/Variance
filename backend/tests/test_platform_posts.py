import pytest

from tests.test_posts import edit_payload, ready


@pytest.mark.parametrize(
    ("platform", "url"),
    [
        ("threads", "https://www.threads.net/@artist/post/example"),
        ("x", "https://twitter.com/artist/status/123"),
    ],
)
def test_platform_editors_approve_and_record_alias_domains(client, platform, url):
    path, art, _ = ready(client)
    post = client.post(
        path + "/posts", json={"artwork_id": art["id"], "platform": platform, "tone": "minimal"}
    ).json()
    post = client.post(
        path + f"/posts/{post['id']}/versions",
        json=edit_payload(post, caption="A new perspective."),
    ).json()
    response = client.post(
        path + f"/posts/{post['id']}/approve", json={"revision": 1, "content_reviewed": True}
    )
    assert response.status_code == 200, response.text
    post = response.json()
    assert post["validation"]["limit"] == (280 if platform == "x" else 500)
    response = client.post(
        path + f"/posts/{post['id']}/publication",
        json={
            "revision": post["revision"],
            "url": url,
            "published_at": "2020-01-01T00:00:00Z",
            "manually_published": True,
        },
    )
    assert response.status_code == 200 and response.json()["publication_method"] == "manual"
