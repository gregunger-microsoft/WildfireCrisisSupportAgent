"""Timeline append/query helpers with in-memory TTL store."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from wildfire_crisis_demo.domain.models import TraceEvent

_store: dict[str, tuple[float, list[TraceEvent]]] = {}
_lock = threading.Lock()
_TTL_SECONDS = 3600  # 1 hour


def store_timeline(correlation_id: str, timeline: list[TraceEvent]) -> None:
    with _lock:
        _store[correlation_id] = (time.monotonic(), timeline)
        _gc()


def get_timeline(correlation_id: str) -> list[TraceEvent] | None:
    with _lock:
        _gc()
        entry = _store.get(correlation_id)
        return entry[1] if entry else None


def _gc() -> None:
    now = time.monotonic()
    expired = [k for k, (ts, _) in _store.items() if now - ts > _TTL_SECONDS]
    for k in expired:
        del _store[k]


def make_event(
    kind: str,
    event_type: str,
    source: str,
    summary: str,
    confidence: int | None = None,
    citations: list[str] | None = None,
    details: dict | None = None,
    stage_name: str | None = None,
    agent_name: str | None = None,
    duration_ms: int | None = None,
    status: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
) -> TraceEvent:
    return TraceEvent(
        timestamp_utc=datetime.now(timezone.utc),
        kind=kind,  # type: ignore[arg-type]
        event_type=event_type,
        source=source,
        summary=summary,
        confidence=confidence,
        citations=citations or [],
        details=details or {},
        stage_name=stage_name,
        agent_name=agent_name,
        duration_ms=duration_ms,
        status=status,  # type: ignore[arg-type]
        trace_id=trace_id,
        span_id=span_id,
    )
