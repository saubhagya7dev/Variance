# Social connections — quick setup

Connection checks are implemented for Instagram, Facebook Pages, Threads and X. You create the developer apps and authorize your own accounts; Variance verifies the resulting tokens. This checkpoint does not provide browser OAuth login, token renewal or live publishing.

## Configure locally

Add these entries to the repository-root `.env` as each account becomes ready. Leave unused entries blank. Never commit tokens or paste them into chat.

```dotenv
META_GRAPH_VERSION=
INSTAGRAM_ACCESS_TOKEN=
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
THREADS_ACCESS_TOKEN=
X_USER_ACCESS_TOKEN=
PUBLISH_ENABLED=false
```

| Connection | What to supply |
| --- | --- |
| Instagram | Professional-account token from **Instagram Login**, not Facebook Login. Set `META_GRAPH_VERSION` to a supported version selected for your Meta app, such as `v25.0`. |
| Facebook | **Page access token** and matching numeric Page ID. Uses the same `META_GRAPH_VERSION`. A personal-profile token is not sufficient. |
| Threads | A Threads user access token with profile access (`threads_basic`). Separate from your Instagram token. |
| X (Twitter) | An **OAuth 2.0 user-context access token** with access to the authenticated-user endpoint; an app-only bearer token is not sufficient. Check your developer access plan and usage costs. |

Restart the backend after editing:

```powershell
Set-Location D:\Code\Projects\Variance\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open **Settings → Your social connections**, refresh configuration, then choose **Check connection** on the relevant card. The same cards are available in Publish when a character project is open.

## What the status means

- **Setup needed:** required local settings are missing.
- **Configured · not verified:** settings exist; no provider request has succeeded yet.
- **Identity verified:** the check returned the account's name and ID. This is a point-in-time result, not a guarantee of publishing permission or future token validity.
- **Check failed:** follow the displayed error. Expired tokens, wrong token type, permissions, API version and API access plans can all prevent verification.

Checks make one read-only request, without automatic retries. Provider quotas or charges may apply. To disconnect, clear the token locally and restart; revoke the token through the provider as needed. Verification results are not stored persistently.

Live posting stays disabled even if `PUBLISH_ENABLED=true` at this checkpoint. Instagram/Facebook approved-post dry runs are available. Threads/X caption constraints, media upload, publishing permissions, retry reconciliation and live posting are future work.

## Official references

- [Meta Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Meta Facebook API collection](https://www.postman.com/meta/facebook/overview)
- [Meta Threads API collection](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api)
- [X authenticated-user endpoint](https://docs.x.com/x-api/users/get-my-user)
