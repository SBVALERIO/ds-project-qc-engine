"""HTTP API for the QC engine.

Local dev: uvicorn qc_engine.api:app --reload
In production this needs its own public host (Render, Fly.io, a small VM,
...) — it is not deployed by the Cloudflare Workers/Next.js front end,
which is a separate project (see ../../frontend). The front end calls
POST /analyze wherever this ends up running, via VITE_ENGINE_API_URL.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine import analyze_pdf
from .models import DocumentOrigin, Finding

app = FastAPI(title="DS Project QC Engine")

# The front end is served from a different origin (Cloudflare Workers)
# than this API, so the browser needs an explicit CORS allowance. Set
# ALLOWED_ORIGINS (comma-separated) once the front end's real domain is
# known; defaults cover local dev only — PDFs may carry client-confidential
# drawings, so this should never fall back to "*" in production.
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
allowed_origins = [origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class AnalyzeResponse(BaseModel):
    findings: list[Finding]


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile,
    origin: Optional[DocumentOrigin] = Form(default=None),
    check_tbd_specs: bool = Form(default=False),
) -> AnalyzeResponse:
    """`origin` should match the upload flow's own choice ("Project
    Package — Revit" / "— AutoCAD" / "Shop Drawings") — several rules
    only know how to interpret the PDF correctly once they know which
    authoring tool produced it (see rules/fixture_quantity.py).

    `check_tbd_specs` flags unresolved ("TBD") finish/material specs —
    off by default since that's expected on an early-stage package;
    callers past that stage (a project already in construction) opt in."""

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Envie um arquivo PDF.")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / (file.filename or "upload.pdf")
        pdf_path.write_bytes(await file.read())
        # analyze_pdf is CPU-bound (PyMuPDF parsing + regex-heavy rules) and
        # synchronous. Calling it directly here would block the whole event
        # loop for the entire analysis — with a single worker process, that
        # freezes every other request (including /health) for as long as
        # this one PDF takes. run_in_threadpool keeps the loop free.
        findings = await run_in_threadpool(
            analyze_pdf, str(pdf_path), origin=origin, check_tbd_specs=check_tbd_specs
        )

    return AnalyzeResponse(findings=findings)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
