# Connections and free operation

Phase 2 defaults to **Wikipedia source extracts + Wikimedia Commons image search**, without accounts or API keys. Local image uploads work independently of search. Results are source material to review, not an assertion that every page or image matches the character's exact incarnation.

## Optional Gemini research

To enable AI research with Google Search grounding, put `RESEARCH_PROVIDER=gemini`, `GEMINI_API_KEY=<your key>` and optionally `GEMINI_MODEL=gemini-3.8-flash` in the root `.env`, then restart the backend. Keys never appear in the UI or API responses. Do not paste keys into chat or commit `.env`.

Use a project **without billing enabled** for free-tier-only use. The application cannot inspect your Google billing account; the configured key determines billing. There is no automatic provider/model fallback and research is not automatically retried. Check your account's quota before each experiment. Gemini is disabled by default and has not been live-tested in this checkout because no key is configured.

Sources checked during implementation:

- [Google grounding API](https://ai.google.dev/gemini-api/docs/generate-content/google-search): source chunks, claim supports and search suggestions.
- [Google pricing](https://ai.google.dev/gemini-api/docs/pricing): free-tier availability varies by model/account; do not assume all Gemini models have free grounding.
- [MediaWiki image metadata](https://www.mediawiki.org/wiki/API:Imageinfo): Commons image URLs, attribution and licence fields.

## Later phases

Generation needs a reference-capable provider and an agreed quality/cost budget. Social publishing needs separate account authorization and token protection. Neither is connected by this phase. Never expose this unauthenticated local server publicly.
