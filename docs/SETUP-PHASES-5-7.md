# Publishing, performance and recovery

Phases 5–7 extend the existing local workflow. Their provider contracts are covered by mocked tests; account permissions, plan access and a real publication still require verification with your own credentials. No live post is created during installation.

## 1. Configure social accounts

Open **Settings → How to set up social accounts** for the platform-specific walkthrough. Store credentials only in repository-root `.env`, then restart the backend. The application accepts user/Page tokens obtained through the provider's developer tooling or your own OAuth client. It does not host an OAuth callback or renew tokens automatically.

| Platform | Settings | Access needed |
| --- | --- | --- |
| Instagram professional | `INSTAGRAM_ACCESS_TOKEN`, `META_GRAPH_VERSION` | Instagram Login token with `instagram_business_basic` and `instagram_business_content_publish` |
| Facebook Page | `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `META_GRAPH_VERSION` | Matching Page token with the appropriate Page read access and `pages_manage_posts` |
| Threads | `THREADS_ACCESS_TOKEN` | `threads_basic`, `threads_content_publish`; add `threads_manage_insights` for measurements |
| X | `X_USER_ACCESS_TOKEN` | OAuth 2.0 user token with `users.read`, `tweet.read`, `tweet.write`, `media.write`; API access/credits as required by your plan |

Use the Graph version supported by your Meta app. Identity checks confirm the account name and numeric ID, not publishing permissions. App roles, review requirements, token expiry and API access restrictions remain provider-controlled.

Official references: [Instagram Login](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login), [Page tokens](https://www.postman.com/meta/facebook/request/tass6hw/get-specific-page-access-token), [Threads API](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api), [X user authorization](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code), [X image upload](https://docs.x.com/x-api/media/upload-media).

## 2. Review and publish

Add these settings when you are ready, preserving your existing keys:

```dotenv
PUBLISH_ENABLED=true
DAILY_POST_CAP=3
METRICS_ENABLED=false
```

Restart the backend. Choose Instagram, Facebook, Threads or X in **Captions & tags**. Edit the caption, disclosure, hashtags and alt text, save a version, then approve it. Threads uses a 500-character studio limit; X uses a conservative 280-unit weighted estimate, including disclosure, hashtags and URLs. These checks do not guarantee platform acceptance.

In **Publish**:

1. Select an approved version and run local preflight.
2. Download its publication JPEG. Instagram additionally requires an aspect ratio between 4:5 and 1.91:1; prepare and approve a suitable image first.
3. For Instagram and Threads, upload that exact JPEG to a public HTTPS image host you control, then paste its URL. Variance checks the downloaded bytes before proceeding. Keep the hosted file unchanged and accessible through publication. The local studio must remain bound to loopback. Facebook and X upload the JPEG directly.
4. Verify the destination and inspect its account name/ID.
5. Check the confirmation for this exact version and account, then click **Publish now**.
6. Inspect the delivery journal for the result and remote ID. Instagram/Threads permalink lookup is not currently included; use the native platform to open those posts.

This release publishes one still image per post. It does not support carousels, video, scheduled posts, bulk publishing or automatic retries. The UTC daily cap covers all accounts and includes uncertain attempts. Stored fingerprints block sending the same image/text to the same destination through another post version, even if only its alt text changed.

If an upload/publish response times out or the process stops, the delivery becomes **uncertain**. Check the native account and enter the existing remote post ID in the journal to reconcile. Variance checks the author and exact text; this does not compare the remote image bytes. Provider text rewriting or missing read permissions can leave an attempt unresolved. Absence from a read response is never treated as permission to resend. Reconciled measurement windows start at verification time, rather than an inferred publication time.

Manual export and self-reported publication records remain available when live publishing is disabled.

## 3. Collect performance snapshots

Set `METRICS_ENABLED=true` and restart. A successful connected publication creates persistent deadlines at **1 hour, 24 hours and 7 days**. The worker checks every 30 seconds while the backend runs. After downtime, overdue samples are collected late and retain both the original deadline and actual collection-attempt timestamp.

The **Performance** page shows native counts returned by the provider: available Instagram likes/comments, Facebook likes/comments/shares, X public post metrics and Threads post insights. There are no invented reach, impression or engagement-rate estimates. Missing fields stay absent; an entire failed/empty response is **unavailable**. Fix permissions/access first, then use **Retry collection**. A retry preserves the deadline and records a new attempt time.

Comparisons use likes from at least three collected samples in the same project, platform, account and window, each within 15 minutes of its deadline. They identify observations worth reviewing, with a clear limitation: audience, time and other factors can explain differences. Manual publication records have no verified native identifiers and are not enrolled in this worker.

## 4. Back up and restore

Open **Settings → Your work, preserved → Download studio backup**. The ZIP contains:

- A consistent SQLite snapshot.
- Every reference/artwork PNG referenced by that snapshot, including archived/removed records.
- A manifest with SHA-256 checksums.

It excludes `.env`, API keys and unrelated local files. The database still contains project content, account identifiers and provider activity, so keep archives private. A missing/corrupt referenced image blocks backup with an actionable error. This release supports backups up to 2 GB uncompressed.

To restore, stop the backend and open a terminal in `backend`:

```powershell
uv run python -m app.backup D:/Backups/variance-backup.zip D:/Backups/variance-restored
```

The destination must be new or empty. Restore validates paths, checksums and SQLite integrity before copying the restored files. Existing work is never overwritten. Point `.env` to the restored paths:

```dotenv
DATABASE_URL=sqlite:///D:/Backups/variance-restored/studio.sqlite3
ASSET_DIR=D:/Backups/variance-restored/assets
```

Restart and verify the projects/images before retiring any old data. Reconfigure tokens separately. Interrupted publications restored from a backup require reconciliation; interrupted read-only metric jobs return to pending. Continue using a single backend process.

Settings also reports database integrity, uncertain deliveries, pending/unavailable measurements and recent provider-call outcomes. Provider logs contain timing/status metadata, not tokens, prompts or raw provider errors.

## Release verification

Verified on 2026-10-21: 101 backend tests passed; Ruff lint/format and frontend ESLint/production build passed. Browser checks covered publishing controls, the Performance empty state, setup popup and backup/status panel. Run backend pytest/Ruff and frontend lint/build as described in the main README. Tests use isolated temporary databases, mocked provider responses and backup round trips. Actual account authorization, API access/charges and final platform acceptance remain external activation checks.
