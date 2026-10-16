# Connections checklist (not required for phases 0–1)

- Gemini: choose grounded text and image models independently, confirm quotas, grounding support and prices in official documentation. A configured key is not proof that an integration is connected.
- Search: select one image-search API after verifying image results, source URLs, cost, quotas and storage terms. Do not scrape search pages.
- Generation: confirm reference-image support and the niche quality bar before choosing a provider. Never fall back to a paid or text-only provider without explicitly allowing it.
- Meta: confirm the chosen Instagram login/authentication flow and its current account/linking requirements, Facebook Page permissions, developer app setup and token lifecycle against official documentation in phase 5.
- X: optional; verify current media/posting/metrics access and costs before implementation.
- Storage: local disk for the MVP. Public media hosting is selected only when a publishing integration needs it.

Keys belong in the root `.env`, never in source, screenshots, prompts or committed files. The current UI exposes configuration status only and never returns secrets. No live provider call is made in phases 0–1. Do not expose the unauthenticated local server to a network.
