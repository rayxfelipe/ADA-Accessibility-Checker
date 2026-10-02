# ADA-Accessibility-Checker
An AI-powered solution that audits PDF documents for ADA (Americans with Disabilities Act) and WCAG (Web Content Accessibility Guidelines) accessibility issues and provides actionable guidance for remediation.

The app uploads a PDF, sends it to a Microsoft Foundry agent (`ADAAccessibilityCheckerAgent`), and renders the agent's accessibility audit in the browser.

## Repository ownership and upstream model

This repository is the maintained LADBS fork of [`snikjou/ADA-Accessibility-Checker`](https://github.com/snikjou/ADA-Accessibility-Checker). The fork provides developer and release independence from the upstream repository while retaining the ability to adopt Said's checker improvements deliberately.

Upstream changes are not production-ready merely because they land on Said's `main` branch. The release process is:

1. Fetch and review changes from the upstream `main` branch.
2. Integrate selected changes into this fork without discarding LADBS integration work.
3. Run checker regression tests.
4. Run the cross-repository JSON contract tests against [`rayxfelipe/PDF-ADA-Remediator`](https://github.com/rayxfelipe/PDF-ADA-Remediator).
5. Validate the complete checker, remediation, download, and remediated-PDF recheck workflow.
6. Promote only the reviewed and validated fork commit as production-ready.
7. Deploy an immutable image built from that approved commit.

The upstream repository is therefore a source of checker improvements, not the production deployment source.

## Two-repository architecture

The customer-facing workflow consists of two independently maintained applications:

1. This checker fork owns the frontend, Microsoft Foundry audit, compliance report, structured findings, remediation JSON generation, and post-remediation recheck experience.
2. [`PDF-ADA-Remediator`](https://github.com/rayxfelipe/PDF-ADA-Remediator) receives the original PDF and checker-generated JSON, applies only supported deterministic changes, and returns a new PDF without overwriting the source.

```text
Browser -> ADA Checker fork -> Microsoft Foundry audit
        -> versioned remediation JSON + original PDF
        -> PDF ADA Remediator -> remediated PDF
        -> ADA Checker fork recheck and comparison
```

The JSON contract is the integration boundary. Neither repository should depend on the other application's presentation or internal implementation.

## Project structure

```
backend/    FastAPI service that talks to the Foundry agent and serves the frontend
frontend/   Static upload UI (HTML/CSS/JS)
```

## Prerequisites

- Python 3.10+
- Access to a Microsoft Foundry project with the `ADAAccessibilityCheckerAgent` prompt agent deployed
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
| `MODEL_DEPLOYMENT_NAME` | Foundry model deployment used by the agent, default `gpt-5` |
| `ENVIRONMENT` | `development` uses `DefaultAzureCredential` (az login); `production` uses `ManagedIdentityCredential` |
| `AZURE_CLIENT_ID` | User-assigned managed identity client ID (production only, optional) |
| `MAX_FILE_SIZE_MB` | Max upload size, default 25 |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins, or `*` |
| `REMEDIATOR_API_URL` | Base URL of the PDF remediator service; enables **Perform remediation** |
| `REMEDIATOR_API_KEY` | Optional shared key sent only by the backend proxy |
| `REMEDIATOR_TIMEOUT_SECONDS` | Remediator request timeout, default 120 seconds |
| `REMEDIATOR_MAX_FILE_SIZE_MB` | Remediation upload limit, default 20 MB |

The desired prompt-agent definition is versioned in `foundry/ADAAccessibilityCheckerAgent.json`. The authoritative 32-rule policy is `backend/app/config.py:AUDIT_PROMPT` and is included with every audit request.

In production, grant the app's managed identity the `Foundry User` role on the Foundry project instead of relying on `DefaultAzureCredential`.

## Checker-remediator contract

The checker emits a version 2 remediation JSON envelope containing structured assessment metadata and the original Markdown report. The structured assessment supplies standards, evidence tier, checker version, summary counts, and stable rule identifiers for the UI. The Markdown field remains present so deployed remediator versions that support the original contract continue to work.

Overview counts are derived from the same structured findings rendered by the dashboard. When a remediated PDF is checked immediately after its original in the same browser session, the dashboard compares rule statuses by stable identifier and distinguishes changed assessment evidence from a demonstrated PDF regression.

The remediation JSON identifies findings and recommended actions, but it is not authorization to invent document meaning. The remediator applies only changes it can make reliably; semantic structure, reading order, alternate-text authorship, and other judgment-dependent work may remain unresolved for a qualified accessibility specialist.
