# ADA-Accessibility-Checker
An AI-powered solution that audits PDF documents for ADA (Americans with Disabilities Act) and WCAG (Web Content Accessibility Guidelines) accessibility issues and provides actionable guidance for remediation.

The app uploads a PDF, sends it to a Microsoft Foundry agent (`ADAAccessibilityCheckerAgent`), and renders the agent's accessibility audit in the browser.

## Project structure

```
backend/    FastAPI service that talks to the Foundry agent and serves the frontend
frontend/   Static upload UI (HTML/CSS/JS)
```

## Prerequisites

- Python 3.10+
- Access to the Foundry project `adaaccessibilitychecker` with the `ADAAccessibilityCheckerAgent` agent deployed
- Signed in with the Azure CLI for local development: `az login`

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust values if needed
```

## Run locally

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser, upload a PDF, and click **Run Accessibility Audit**.

## Configuration

Set these in `backend/.env` (see `backend/.env.example`):

| Variable | Description |
|---|---|
| `PROJECT_ENDPOINT` | Foundry project endpoint |
| `AGENT_NAME` | Name of the deployed agent |
| `ENVIRONMENT` | `development` uses `DefaultAzureCredential` (az login); `production` uses `ManagedIdentityCredential` |
| `AZURE_CLIENT_ID` | User-assigned managed identity client ID (production only, optional) |
| `MAX_FILE_SIZE_MB` | Max upload size, default 25 |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins, or `*` |
| `REMEDIATOR_API_URL` | Base URL of the PDF remediator service; enables **Perform remediation** |
| `REMEDIATOR_API_KEY` | Optional shared key sent only by the backend proxy |
| `REMEDIATOR_TIMEOUT_SECONDS` | Remediator request timeout, default 120 seconds |
| `REMEDIATOR_MAX_FILE_SIZE_MB` | Remediation upload limit, default 20 MB |

In production, grant the app's managed identity the appropriate RBAC role on the Foundry project instead of relying on `DefaultAzureCredential`.
