"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI

from wildfire_crisis_demo.app.routes import router
from wildfire_crisis_demo.observability import setup_observability

setup_observability()

app = FastAPI(
    title="Wildfire Crisis Response Coordination Agent",
    version="0.1.0",
    description="Multi-agent decision support for wildfire crisis coordination. DECISION SUPPORT ONLY.",
)
app.include_router(router)
