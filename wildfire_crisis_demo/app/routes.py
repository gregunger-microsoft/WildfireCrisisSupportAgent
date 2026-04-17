"""FastAPI routes."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from wildfire_crisis_demo.app.deps import get_foundry_client
from wildfire_crisis_demo.domain.models import (
    CoordinationResponse,
    WildfireIncidentBundle,
)
from wildfire_crisis_demo.services.orchestrator import OrchestrationError, run_pipeline
from wildfire_crisis_demo.services.timeline import get_timeline

router = APIRouter()

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_payloads"
UI_DIR = Path(__file__).resolve().parent.parent / "ui"


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = UI_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@router.get("/api/samples/{name}")
async def get_sample(name: str) -> JSONResponse:
    # Sanitize name to prevent path traversal
    safe = Path(name).name
    if safe != name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid sample name")
    path = SAMPLE_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Sample '{name}' not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    return JSONResponse(content=data)


@router.post("/crisis/coordinate")
async def coordinate(bundle: WildfireIncidentBundle) -> CoordinationResponse:
    client = get_foundry_client()
    try:
        return await run_pipeline(bundle, client)
    except OrchestrationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/crisis/trace/{correlation_id}")
async def get_trace(correlation_id: str) -> JSONResponse:
    timeline = get_timeline(correlation_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return JSONResponse(content=[e.model_dump(mode="json") for e in timeline])
