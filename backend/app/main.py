"""FastAPI application exposing the PDF ADA Accessibility Checker."""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@app.get("/api/health")
def health_check():
    return {"status": "ok", "agent": config.AGENT_NAME}


@app.post("/api/audit")
async def audit_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
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

    try:
        result = foundry_agent_client.audit_pdf(tmp_path, file.filename)
    except AgentAuditError as exc:
        logger.error("Agent audit failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the client
        logger.exception("Unexpected error while auditing PDF")
        raise HTTPException(status_code=500, detail="Unexpected error while auditing the document.") from exc
    finally:
        os.unlink(tmp_path)

    return JSONResponse(
        {
            "filename": file.filename,
            "threadId": result.thread_id,
            "runId": result.run_id,
            "report": result.response_text,
        }
    )


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
