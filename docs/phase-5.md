# Phase 5 — authorized publishing

Targets: the owner's Instagram professional account, Facebook Page, Threads and X accounts. Work on main with one commit per changed file and a completion checkpoint per feature. No pushes.

## Delivery steps

1. **Local dry run:** publishing workspace, approved post selection, revision/artwork/file checks, content preview, explicit unresolved connection blockers. Never send a post during preflight.
2. **Account setup:** verify the Meta app and login route, destination IDs, publishing permissions and token lifecycle. Keep tokens server-side in local secrets; display verified account identity without returning credentials. Check whether the Instagram account is linked to the Facebook Page before choosing a shared login flow.
3. **Live adapter:** implement the verified API contract for each platform, media preparation and upload, explicit confirmation for the selected destination and post revision, and a persistent publication attempt record.
4. **Recovery:** reserve daily capacity transactionally, deduplicate attempts for the same post/destination, persist remote IDs, and reconcile ambiguous network outcomes before any retry. Never retry an uncertain publish blindly.
5. **Acceptance:** mock provider success/failure tests, restart/recovery and concurrent-submit tests, UI verification, then an owner-approved live post to each connected destination.

## Current checkpoint

The local dry-run workspace and API are implemented for Instagram/Facebook posts. Four account identity-check adapters and configuration cards are implemented; see [social connection setup](SOCIAL-CONNECTIONS.md). The owner will create the accounts/apps and add local credentials later. Browser OAuth login, token refresh, live publishing adapters, Threads/X post composition, persistent publication attempts, daily-limit enforcement and reconciliation remain pending. Dry-run success means the saved content is ready for connection checks; it does not mean a platform accepted or published it. `PUBLISH_ENABLED` does not enable live publishing at this checkpoint.

## Owner setup information needed next

- A Meta developer app for the intended accounts, or confirmation that it still needs creating.
- Whether the Instagram professional account is linked to the Facebook Page.
- The chosen login route and permissions must be checked against Meta's current documentation before credentials are requested.
- For URL-based Instagram media ingestion, decide how the prepared image will be available to Meta; localhost is not a public media host. Do not expose the local studio itself.

Tokens should be added only to local configuration when the connection adapter is ready, never pasted into chat or committed.

## References

- [Instagram publishing documentation](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing)
- [Facebook Page posts](https://developers.facebook.com/docs/pages-api/posts/)

Direct Meta documentation retrieval was unavailable during the first checkpoint; the connection adapters use documented account-read routes from official provider references. Live account verification remains pending credentials. No live publishing contract is implemented here.
