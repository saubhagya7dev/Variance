# Phase 3: creative direction and image review

## Current image route

Cloudflare generation is retired. Use Gemini's daily-limited image tool through the manual workflow: download a frozen prompt/reference pack, open Gemini, attach references and paste the prompt, then import results into the same batch. The allowance depends on your Gemini account; Variance cannot inspect or bypass it.

## Optional API adapter

Gemini image API access is separate from the Gemini tool and has no published free tier. The adapter defaults to `gemini-nano-banana-2.1` and remains disabled unless both `GEMINI_API_KEY` and explicit `GEMINI_IMAGE_PAID_ENABLED=true` are configured. A key used for captions or research alone does not enable it. No billing changes or live paid API calls were made during implementation.

The Interactions API receives the saved prompt and up to four reference images, resized to at most 1536px per side. Output requests use 1K and the saved aspect ratio. Payloads/results are bounded; incomplete, text-only or malformed responses fail rather than becoming fake artwork. Tests use mocked provider responses.

## Persistence and migration

Prompt versions freeze identity, research and references. Manual packs allow up to eight selected references. Batches contain one to four images; reviews and notes persist with revision protection. Back up the database together with all reference and artwork files.

New API batches snapshot the Gemini provider and model. Existing Cloudflare batches retain their provider/model and results. Queued or running legacy jobs are interrupted during migration; they are never silently sent to Gemini. Interrupted generation is not automatically retried, because the provider may have processed the request. Partial results remain available.

## Quality review

Local template/manual workflows remain keyless. Live Gemini model access and real image quality require separate owner evaluation. No guarantee of better output is implied by replacing the provider. Review identity, anatomy, composition and suitability before approval.

See [README](../README.md) and [complete setup guide](SETUP-PHASES-1-4.md) for current configuration and usage.

Official references:
- [Image generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Interactions API](https://ai.google.dev/api/interactions-api)
- [Pricing](https://ai.google.dev/gemini-api/docs/pricing)
