"""FastAPI application exposing the PDF ADA Accessibility Checker."""

import logging
import tempfile
import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
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


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
