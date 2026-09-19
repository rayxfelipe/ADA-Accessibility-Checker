"""FastAPI application exposing the PDF ADA Accessibility Checker."""

import json
import logging
import tempfile
import threading
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from . import config
from .foundry_client import AgentAuditError, foundry_agent_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ada_checker.main")

app = FastAPI(title="ADA Accessibility Checker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
audit_jobs: dict[str, dict[str, str]] = {}
audit_jobs_lock = threading.Lock()


def _update_audit_job(job_id: str, **values: str) -> None:
    with audit_jobs_lock:
        audit_jobs[job_id].update(values)


def _run_audit_job(job_id: str, file_path: str, filename: str) -> None:
    _update_audit_job(job_id, status="running")
    try:
        result = foundry_agent_client.audit_pdf(file_path, filename)
        _update_audit_job(
            job_id,
            status="completed",
            threadId=result.thread_id,
            runId=result.run_id,
            report=result.response_text,
        )
    except AgentAuditError as exc:
        logger.error("Agent audit failed: %s", exc)
        _update_audit_job(job_id, status="failed", error=str(exc))
    except Exception:  # noqa: BLE001 - preserve a clean error for the client
        logger.exception("Unexpected error while auditing PDF")
        _update_audit_job(
            job_id,
            status="failed",
            error="Unexpected error while auditing the document.",
        )
    finally:
        Path(file_path).unlink(missing_ok=True)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "agent": config.AGENT_NAME}


@app.post("/api/audit", status_code=202)
async def audit_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    filename = file.filename or "document.pdf"
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {config.MAX_FILE_SIZE_MB}MB size limit.",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    job_id = uuid.uuid4().hex
    with audit_jobs_lock:
        audit_jobs[job_id] = {"jobId": job_id, "status": "queued", "filename": filename}
    background_tasks.add_task(_run_audit_job, job_id, tmp_path, filename)
    return {"jobId": job_id, "status": "queued", "filename": filename}


@app.get("/api/audit/{job_id}")
def get_audit_job(job_id: str):
    with audit_jobs_lock:
        job = audit_jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Audit job was not found.")
        return dict(job)


@app.post("/api/remediate")
async def remediate_pdf(
    file: UploadFile = File(...),
    remediation_report: str = Form(...),
):
    if not config.REMEDIATOR_API_URL:
        raise HTTPException(status_code=503, detail="PDF remediation is not configured.")

    filename = (file.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    contents = await file.read()
    if not contents or not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
    if len(contents) > config.REMEDIATOR_MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Remediation supports PDFs up to {config.REMEDIATOR_MAX_FILE_SIZE_MB}MB.",
        )

    report_bytes = remediation_report.encode("utf-8")
    if len(report_bytes) > config.REMEDIATION_REPORT_MAX_BYTES:
        raise HTTPException(status_code=400, detail="The remediation report is too large.")
    try:
        report = json.loads(remediation_report)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="The remediation report is not valid JSON.") from exc
    if not isinstance(report, dict) or report.get("fileName") != filename or not isinstance(report.get("remediationReport"), str):
        raise HTTPException(status_code=400, detail="The remediation report does not match the uploaded PDF.")

    headers = {}
    if config.REMEDIATOR_API_KEY:
        headers["X-Remediator-Key"] = config.REMEDIATOR_API_KEY
    files = {
        "file": (filename, contents, "application/pdf"),
        "remediation_report": ("remediation-report.json", report_bytes, "application/json"),
    }
    try:
        async with httpx.AsyncClient(timeout=config.REMEDIATOR_TIMEOUT_SECONDS) as client:
            remediator_response = await client.post(
                f"{config.REMEDIATOR_API_URL}/api/remediate",
                files=files,
                headers=headers,
            )
    except httpx.RequestError as exc:
        logger.warning("PDF remediation service request failed: %s", exc)
        raise HTTPException(status_code=502, detail="The PDF remediation service is unavailable.") from exc

    if remediator_response.status_code != 200:
        logger.warning("PDF remediation service returned HTTP %s", remediator_response.status_code)
        detail = "The remediation report could not be applied."
        raise HTTPException(status_code=400 if remediator_response.status_code == 400 else 502, detail=detail)
    if remediator_response.headers.get("content-type", "").split(";", 1)[0] != "application/pdf" or not remediator_response.content.startswith(b"%PDF-"):
        raise HTTPException(status_code=502, detail="The remediation service returned an invalid PDF.")
    if len(remediator_response.content) > config.REMEDIATOR_MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=502, detail="The remediation service returned an oversized PDF.")

    output_name = f"{Path(filename).stem}_remediated.pdf"
    return Response(
        content=remediator_response.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(output_name, safe='')}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
