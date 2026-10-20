from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.models import timestamp

router = APIRouter(prefix="/api/connections", tags=["connections"])
Platform = Literal["instagram", "facebook", "threads", "x"]
FIELDS = {
    "instagram": ("instagram_access_token", "meta_graph_version"),
    "facebook": ("facebook_page_access_token", "facebook_page_id", "meta_graph_version"),
    "threads": ("threads_access_token",),
    "x": ("x_user_access_token",),
}


@router.get("")
def connections(request: Request):
    config = request.app.state.config
    return [
        {
            "platform": platform,
            "configured": all(bool(getattr(config, field).strip()) for field in fields),
            "missing": [field.upper() for field in fields if not getattr(config, field).strip()],
            "status": "not_verified",
            "publishing_enabled": False,
        }
        for platform, fields in FIELDS.items()
    ]


@router.post("/{platform}/check")
async def check(platform: Platform, request: Request):
    config = request.app.state.config
    if not all(getattr(config, field).strip() for field in FIELDS[platform]):
        raise HTTPException(409, "Add the required settings to local .env and restart the backend.")
    version = config.meta_graph_version
    endpoints = {
        "instagram": (
            f"https://graph.instagram.com/{version}/me",
            "user_id,username",
            config.instagram_access_token,
        ),
        "facebook": (
            f"https://graph.facebook.com/{version}/me",
            "id,name",
            config.facebook_page_access_token,
        ),
        "threads": ("https://graph.threads.net/me", "id,username", config.threads_access_token),
        "x": ("https://api.x.com/2/users/me", "", config.x_user_access_token),
    }
    url, fields, token = endpoints[platform]
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as client:
            response = await client.get(
                url,
                params={"fields": fields} if fields else {},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        body = response.json()
        identity = body.get("data", {}) if platform == "x" else body
        account_id = identity.get("user_id") if platform == "instagram" else identity.get("id")
        name = identity.get("username") or identity.get("name")
        if (
            not isinstance(account_id, str)
            or not account_id.isdecimal()
            or not isinstance(name, str)
            or not name.strip()
        ):
            raise ValueError()
        if platform == "facebook" and account_id != config.facebook_page_id:
            raise HTTPException(
                409,
                "This token does not identify the configured Facebook Page. Use that Page's access token.",
            )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        advice = "Check the token, permissions and developer-app access."
        if status == 429:
            advice = "Rate limit reached; wait before checking again."
        elif status == 402:
            advice = "Review the provider's API access plan or credits."
        raise HTTPException(502, f"Account check failed (HTTP {status}). {advice}") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach the provider. Try again later.") from None
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(502, "Provider returned an unexpected account response.") from None
    return {
        "platform": platform,
        "status": "identity_verified",
        "account_id": account_id,
        "name": name[:200],
        "checked_at": timestamp(),
        "publishing_enabled": False,
        "message": "Account identity verified. Publishing permissions and live posting are not enabled by this check.",
    }
