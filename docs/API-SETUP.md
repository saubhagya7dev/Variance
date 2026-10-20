# Variance — API connection quick setup

Use this guide after the app is installed. For first-time installation, see [README](../README.md#quick-start).

## 1. Choose what to connect

| Feature | Setup |
| --- | --- |
| Wikipedia research and Wikimedia references | Works without keys |
| Gemini research and caption drafting | Optional Gemini API key; steps below |
| Gemini daily-limited image tool | Manual generation and import; no API key needed |
| Direct image API generation | Separate paid opt-in; leave disabled for the manual workflow |

## 2. Add your Gemini text API key

Create or select a key in [Google AI Studio](https://aistudio.google.com/apikey). Use a project without billing enabled if you want to stay within eligible free text usage; model availability and quotas depend on your account. See [Google's key setup guide](https://ai.google.dev/gemini-api/docs/api-key).

From PowerShell, create the configuration file only if it is missing:

```powershell
Set-Location D:\Code\Projects\Variance
if (!(Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
notepad .env
```

Update these entries in the existing file, replacing the placeholder with your key:

```dotenv
GEMINI_API_KEY=your_key_here
RESEARCH_PROVIDER=gemini
GEMINI_MODEL=gemini-3.8-flash
GEMINI_CAPTIONS_ENABLED=true
GEMINI_IMAGE_PAID_ENABLED=false
```

Keep the key in the repository-root `.env`, never in frontend code or Git. To use only keyless features, keep `RESEARCH_PROVIDER=wikipedia` and `GEMINI_CAPTIONS_ENABLED=false`.

## 3. Restart and check the connection

Stop the existing backend with **Ctrl+C**, then start it again:

```powershell
Set-Location D:\Code\Projects\Variance\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open [Variance](http://127.0.0.1:8765/) and refresh the page. In another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Invoke-RestMethod http://127.0.0.1:8765/api/capabilities |
    ConvertTo-Json -Depth 4
```

Expect health `status: ok`, research `provider: gemini`, and captions `configured: true`. Image generation `configured: false` is intentional.

These checks confirm local configuration, not Google's acceptance of your key. Run one character research request or one Gemini caption draft in the app to verify the actual API connection; it consumes your API quota.

## 4. Generate images with your Gemini tool allowance

In Variance: **create a manual batch → download the prompt/reference pack → Open Gemini → attach references and generate → download the result → import into the same batch**.

The Gemini website's allowance does not connect to the API key. Keep `GEMINI_IMAGE_PAID_ENABLED=false` for this workflow. Direct image API use has separate pricing and quotas; review [Google's API pricing](https://ai.google.dev/gemini-api/docs/pricing) before deliberately enabling it.

## Quick fixes

| Problem | Check |
| --- | --- |
| Cannot connect to localhost | Backend is running on port 8765 |
| Settings appear unchanged | File is `Variance\.env`, not `.env.txt`; restart backend |
| Key rejected or access denied | Correct key/project, Gemini API access and key restrictions in AI Studio |
| Quota exhausted | Wait for the provider's reset or use Wikipedia/local captions |
| Model unavailable | Choose an accessible text model in `GEMINI_MODEL`, then restart |

Social-platform API connections arrive in Phase 5; they are not required for Phases 1–4.
