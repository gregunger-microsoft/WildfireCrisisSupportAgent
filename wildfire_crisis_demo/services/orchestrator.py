"""Pipeline orchestration with timeline recording."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from wildfire_crisis_demo.domain.models import (
    CrisisActionBrief,
    CoordinationResponse,
    IncidentSnapshot,
    ResourcePlan,
    SitRep,
    SupervisorReview,
    TraceEvent,
    WildfireIncidentBundle,
)
from wildfire_crisis_demo.domain.policy import enforce_supervisor_policy
from wildfire_crisis_demo.foundry.client import FoundryClientBase
from wildfire_crisis_demo.services.prompts import (
    BRIEF_PROMPT,
    DATA_INGEST_PROMPT,
    REPAIR_PROMPT,
    RESOURCE_ALLOCATOR_PROMPT,
    SITREP_PROMPT,
    SUPERVISOR_PROMPT,
)
from wildfire_crisis_demo.services.timeline import make_event, store_timeline
from wildfire_crisis_demo.ui.render import brief_to_markdown

logger = logging.getLogger(__name__)


class OrchestrationError(Exception):
    pass


async def _run_agent_with_validation(
    client: FoundryClientBase,
    agent_name: str,
    system_prompt: str,
    user_message: str,
    schema_cls: type,
    timeline: list[TraceEvent],
    stage_name: str,
    correlation_id: str,
) -> Any:
    """Run agent, validate output, repair once if needed."""
    start = time.monotonic()
    timeline.append(make_event(
        kind="AGENT_EXECUTION",
        event_type="AGENT_START",
        source="AGENT",
        summary=f"{agent_name} started",
        stage_name=stage_name,
        agent_name=agent_name,
        status="ok",
    ))

    raw = await client.run_agent(agent_name, system_prompt, user_message)

    # Parse and validate
    try:
        parsed = _parse_json(raw)
        result = schema_cls.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        # Repair attempt
        logger.warning("Agent %s invalid output, attempting repair: %s", agent_name, e)
        timeline.append(make_event(
            kind="AGENT_EXECUTION",
            event_type="AGENT_REPAIR",
            source="AGENT",
            summary=f"{agent_name} output invalid, repair attempt",
            stage_name=stage_name,
            agent_name=agent_name,
            status="retry",
            details={"error": str(e)[:500]},
        ))
        repair_msg = REPAIR_PROMPT.format(error=str(e)[:500]) + "\n\nOriginal output:\n" + raw[:2000]
        raw2 = await client.run_agent(agent_name, system_prompt, repair_msg)
        try:
            parsed2 = _parse_json(raw2)
            result = schema_cls.model_validate(parsed2)
        except (json.JSONDecodeError, ValidationError) as e2:
            duration_ms = int((time.monotonic() - start) * 1000)
            timeline.append(make_event(
                kind="ERROR",
                event_type="AGENT_FAIL",
                source="AGENT",
                summary=f"{agent_name} failed after repair attempt",
                stage_name=stage_name,
                agent_name=agent_name,
                duration_ms=duration_ms,
                status="failed",
                details={"error": str(e2)[:500]},
            ))
            raise OrchestrationError(
                f"{agent_name} output invalid after repair: {e2}"
            ) from e2

    duration_ms = int((time.monotonic() - start) * 1000)
    timeline.append(make_event(
        kind="AGENT_EXECUTION",
        event_type="AGENT_END",
        source="AGENT",
        summary=f"{agent_name} completed in {duration_ms}ms",
        stage_name=stage_name,
        agent_name=agent_name,
        duration_ms=duration_ms,
        status="ok",
    ))
    return result


def _parse_json(raw: str) -> dict:
    """Extract JSON from raw text, handling markdown code fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def _add_incident_events(bundle: WildfireIncidentBundle, timeline: list[TraceEvent]) -> None:
    """Extract key incident events from the bundle into the timeline."""
    for w in bundle.weather_feed:
        timeline.append(make_event(
            kind="INCIDENT", event_type="WEATHER_UPDATE", source="WEATHER",
            summary=w.summary, confidence=None, citations=[w.id],
            details={"wind_speed_mph": w.wind_speed_mph, "wind_direction": w.wind_direction},
        ))
    for fb in bundle.fire_behavior:
        timeline.append(make_event(
            kind="INCIDENT", event_type="FIRE_BEHAVIOR", source="FIRE",
            summary=fb.summary, confidence=None, citations=[fb.id],
            details={"perimeter_acres": fb.perimeter_acres, "containment_pct": fb.containment_pct},
        ))
    for inc in bundle.incident_feed:
        timeline.append(make_event(
            kind="INCIDENT", event_type=inc.event_type, source="911",
            summary=inc.summary, confidence=None, citations=[inc.id],
        ))
    for rc in bundle.road_closures:
        timeline.append(make_event(
            kind="INCIDENT", event_type="ROAD_CLOSURE", source="ROADCLOSURE",
            summary=f"{rc.road_name} {rc.segment}: {rc.status}", confidence=None, citations=[rc.id],
        ))
    for ev in bundle.evacuation:
        timeline.append(make_event(
            kind="INCIDENT", event_type="EVAC_ORDER", source="EVAC",
            summary=ev.summary, confidence=None, citations=[ev.id],
        ))
    for sh in bundle.shelters:
        timeline.append(make_event(
            kind="INCIDENT", event_type="SHELTER_STATUS", source="SHELTER",
            summary=sh.summary, confidence=None, citations=[sh.id],
            details={"occupancy_pct": round(sh.current_occupancy / max(sh.capacity, 1) * 100, 1)},
        ))
    for ut in bundle.utilities:
        timeline.append(make_event(
            kind="INCIDENT", event_type="UTILITY_STATUS", source="UTILITIES",
            summary=ut.summary, confidence=None, citations=[ut.id],
        ))
    for aq in bundle.air_quality:
        timeline.append(make_event(
            kind="INCIDENT", event_type="AIR_QUALITY", source="WEATHER",
            summary=aq.summary, confidence=None, citations=[aq.id],
            details={"aqi": aq.aqi, "pm25": aq.pm25},
        ))


async def run_pipeline(
    bundle: WildfireIncidentBundle,
    client: FoundryClientBase,
    correlation_id: str | None = None,
) -> CoordinationResponse:
    """Execute the full multi-agent coordination pipeline."""
    correlation_id = correlation_id or str(uuid.uuid4())
    timeline: list[TraceEvent] = []
    timings: dict[str, float] = {}

    log_ctx = {"correlation_id": correlation_id}
    logger.info("Pipeline started", extra=log_ctx)

    # Stage 0: init timeline
    timeline.append(make_event(
        kind="AGENT_EXECUTION", event_type="PIPELINE_START", source="AGENT",
        summary="Coordination pipeline started", stage_name="init",
    ))
    _add_incident_events(bundle, timeline)

    bundle_json = bundle.model_dump_json()

    # Stage 1: DataIngest
    t0 = time.monotonic()
    snapshot = await _run_agent_with_validation(
        client, "DataIngestAgent", DATA_INGEST_PROMPT, bundle_json,
        IncidentSnapshot, timeline, "DataIngest", correlation_id,
    )
    timings["DataIngest"] = round(time.monotonic() - t0, 3)

    snapshot_json = snapshot.model_dump_json()

    # Stage 2: SitRep + ResourceAllocator in parallel
    t1 = time.monotonic()
    sitrep_task = _run_agent_with_validation(
        client, "SitRepAgent", SITREP_PROMPT, snapshot_json,
        SitRep, timeline, "SitRep", correlation_id,
    )
    resource_task = _run_agent_with_validation(
        client, "ResourceAllocatorAgent", RESOURCE_ALLOCATOR_PROMPT,
        snapshot_json + "\n\nConstraints:\n" + bundle.constraints.model_dump_json(),
        ResourcePlan, timeline, "ResourceAllocator", correlation_id,
    )
    sitrep, resource_plan = await asyncio.gather(sitrep_task, resource_task)
    timings["SitRep+ResourceAllocator"] = round(time.monotonic() - t1, 3)

    # Stage 3: Supervisor
    t2 = time.monotonic()
    # Run local policy check first
    policy_decision, violations, flags = enforce_supervisor_policy(snapshot, sitrep, resource_plan)

    if policy_decision == "BLOCK":
        timeline.append(make_event(
            kind="POLICY", event_type="SUPERVISOR_BLOCK", source="AGENT",
            summary=f"Policy engine blocked: {'; '.join(violations)}",
            stage_name="Supervisor", agent_name="SupervisorAgent",
            status="blocked", details={"violations": violations},
        ))
        raise OrchestrationError(f"Pipeline blocked by policy: {violations}")

    # Also run Foundry supervisor agent for additional review
    supervisor_input = json.dumps({
        "snapshot": snapshot.model_dump(),
        "sitrep": sitrep.model_dump(),
        "resource_plan": resource_plan.model_dump(),
        "policy_flags": flags,
        "policy_violations": violations,
    }, default=str)

    supervisor_review: SupervisorReview = await _run_agent_with_validation(
        client, "SupervisorAgent", SUPERVISOR_PROMPT, supervisor_input,
        SupervisorReview, timeline, "Supervisor", correlation_id,
    )

    if supervisor_review.decision == "BLOCK":
        timeline.append(make_event(
            kind="POLICY", event_type="SUPERVISOR_BLOCK", source="AGENT",
            summary=f"Supervisor blocked: {supervisor_review.policy_violations}",
            stage_name="Supervisor", agent_name="SupervisorAgent",
            status="blocked",
            details={"violations": supervisor_review.policy_violations},
        ))
        raise OrchestrationError(
            f"Supervisor blocked pipeline: {supervisor_review.policy_violations}"
        )

    timeline.append(make_event(
        kind="POLICY", event_type="SUPERVISOR_DECISION", source="AGENT",
        summary=f"Supervisor decision: {supervisor_review.decision}",
        confidence=supervisor_review.confidence,
        stage_name="Supervisor", agent_name="SupervisorAgent",
        status="ok",
        details={"decision": supervisor_review.decision, "flags": supervisor_review.flags},
    ))
    timings["Supervisor"] = round(time.monotonic() - t2, 3)

    # Stage 4: Brief
    t3 = time.monotonic()
    brief_input = json.dumps({
        "snapshot": snapshot.model_dump(),
        "sitrep": sitrep.model_dump(),
        "resource_plan": resource_plan.model_dump(),
        "supervisor_review": supervisor_review.model_dump(),
        "correlation_id": correlation_id,
    }, default=str)

    brief: CrisisActionBrief = await _run_agent_with_validation(
        client, "BriefAgent", BRIEF_PROMPT, brief_input,
        CrisisActionBrief, timeline, "Brief", correlation_id,
    )
    # Inject correlation_id into metadata
    brief.metadata["correlation_id"] = correlation_id
    timings["Brief"] = round(time.monotonic() - t3, 3)

    timeline.append(make_event(
        kind="AGENT_EXECUTION", event_type="PIPELINE_END", source="AGENT",
        summary="Pipeline completed successfully",
        stage_name="complete",
        status="ok",
        duration_ms=int(sum(timings.values()) * 1000),
    ))

    total = sum(timings.values())
    timings["total"] = round(total, 3)

    # Store timeline
    store_timeline(correlation_id, timeline)

    brief_md = brief_to_markdown(brief, correlation_id, timings)

    logger.info("Pipeline completed in %.3fs", total, extra=log_ctx)

    return CoordinationResponse(
        crisis_action_brief=brief,
        brief_markdown=brief_md,
        timings=timings,
        correlation_id=correlation_id,
        trace_timeline=timeline,
    )
