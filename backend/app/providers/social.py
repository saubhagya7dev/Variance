"""Single-image publishing. Writes are never retried automatically."""

import asyncio
import base64
import re

import httpx


def remote_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:_[0-9]+)?", value):
        raise ValueError("Provider did not return a valid remote identifier.")
    return value


def connection(config, platform):
    if platform == "instagram":
        return (
            f"https://graph.instagram.com/{config.meta_graph_version}",
            config.instagram_access_token,
        )
    if platform == "facebook":
        return (
            f"https://graph.facebook.com/{config.meta_graph_version}",
            config.facebook_page_access_token,
        )
    if platform == "threads":
        return "https://graph.threads.net/v1.0", config.threads_access_token
    if platform == "x":
        return "https://api.x.com/2", config.x_user_access_token
    raise ValueError("Unsupported publication platform.")


async def api(client, method, url, **kwargs):
    async with client.stream(method, url, **kwargs) as response:
        response.raise_for_status()
        data = bytearray()
        async for chunk in response.aiter_bytes():
            data.extend(chunk)
            if len(data) > 1_000_000:
                raise ValueError("Provider response exceeded the size limit.")
    import json

    body = json.loads(data) if data else {}
    if not isinstance(body, dict) or body.get("error") or body.get("errors"):
        raise ValueError("Provider returned an incomplete response.")
    return body


async def publish(config, delivery, content, jpeg, public_url, save_container):
    base, token = connection(config, delivery.platform)
    async with httpx.AsyncClient(
        timeout=40,
        trust_env=False,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        if delivery.platform in ("instagram", "threads"):
            threads = delivery.platform == "threads"
            edge = "threads" if threads else "media"
            data = {
                "image_url": public_url,
                "alt_text": content["alt_text"],
                "text" if threads else "caption": content["post_text"],
            }
            if threads:
                data["media_type"] = "IMAGE"
            result = await api(client, "POST", f"{base}/{delivery.account_id}/{edge}", data=data)
            container = remote_id(result.get("id"))
            save_container(container)
            field = "status" if threads else "status_code"
            for _ in range(10):
                result = await api(client, "GET", f"{base}/{container}", params={"fields": field})
                state = result.get(field)
                if state == "FINISHED":
                    break
                if state in ("ERROR", "EXPIRED", "PUBLISHED"):
                    raise ValueError("Container requires reconciliation.")
                await asyncio.sleep(2)
            else:
                raise ValueError("Container is not ready; no publish request was sent.")
            result = await api(
                client,
                "POST",
                f"{base}/{delivery.account_id}/{edge}_publish",
                data={"creation_id": container},
            )
            return remote_id(result.get("id"))
        if delivery.platform == "facebook":
            result = await api(
                client,
                "POST",
                f"{base}/{delivery.account_id}/photos",
                data={
                    "message": content["post_text"],
                    "alt_text_custom": content["alt_text"],
                    "published": "true",
                },
                files={"source": ("artwork.jpg", jpeg, "image/jpeg")},
            )
            return remote_id(result.get("post_id") or result.get("id"))
        result = await api(
            client,
            "POST",
            f"{base}/media/upload",
            json={"media": base64.b64encode(jpeg).decode(), "media_category": "tweet_image"},
        )
        media = remote_id(result.get("data", {}).get("id"))
        save_container(media)
        processing = result.get("data", {}).get("processing_info", {})
        if processing.get("state") not in (None, "succeeded"):
            raise ValueError("X image processing did not finish; no post was sent.")
        await api(
            client,
            "POST",
            f"{base}/media/metadata",
            json={"id": media, "metadata": {"alt_text": {"text": content["alt_text"]}}},
        )
        result = await api(
            client,
            "POST",
            f"{base}/tweets",
            json={"text": content["post_text"], "media": {"media_ids": [media]}},
        )
        return remote_id(result.get("data", {}).get("id"))


async def read_post(config, platform, post_id):
    """Return a remote post for reconciliation; absence is never treated as safe-to-retry."""
    post_id = remote_id(post_id)
    base, token = connection(config, platform)
    async with httpx.AsyncClient(
        timeout=25,
        trust_env=False,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        if platform == "x":
            body = await api(
                client,
                "GET",
                f"{base}/tweets/{post_id}",
                params={"tweet.fields": "author_id,created_at,public_metrics"},
            )
            post = body["data"]
            return {
                "id": post["id"],
                "owner": post.get("author_id"),
                "text": post.get("text", ""),
                "url": f"https://x.com/i/status/{post_id}",
                "metrics": post.get("public_metrics", {}),
            }
        fields = {
            "instagram": "id,caption,owner,permalink,like_count,comments_count",
            "threads": "id,text,username,permalink",
            "facebook": "id,message,from,permalink_url,likes.limit(0).summary(true),comments.limit(0).summary(true),shares",
        }[platform]
        post = await api(client, "GET", f"{base}/{post_id}", params={"fields": fields})
        if platform == "instagram":
            metrics = {"likes": post.get("like_count"), "comments": post.get("comments_count")}
            owner = post.get("owner", {})
            owner = owner.get("id") if isinstance(owner, dict) else owner
        elif platform == "facebook":
            metrics = {
                "likes": post.get("likes", {}).get("summary", {}).get("total_count"),
                "comments": post.get("comments", {}).get("summary", {}).get("total_count"),
                "shares": post.get("shares", {}).get("count"),
            }
            owner = post.get("from", {}).get("id")
        else:
            owner, metrics = post.get("username"), {}
        return {
            "id": post["id"],
            "owner": owner,
            "text": post.get("caption", post.get("message", post.get("text", ""))),
            "url": post.get("permalink", post.get("permalink_url", "")),
            "metrics": metrics,
        }


async def metrics(config, delivery):
    if delivery.platform != "threads":
        return (await read_post(config, delivery.platform, delivery.remote_id))["metrics"]
    base, token = connection(config, "threads")
    async with httpx.AsyncClient(
        timeout=25,
        trust_env=False,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        body = await api(
            client,
            "GET",
            f"{base}/{remote_id(delivery.remote_id)}/insights",
            params={"metric": "views,likes,replies,reposts,quotes"},
        )
        result = {}
        for item in body.get("data", []):
            values = item.get("values") or []
            if isinstance(item.get("name"), str) and values and isinstance(values[0], dict):
                result[item["name"]] = values[0].get("value")
        return result
