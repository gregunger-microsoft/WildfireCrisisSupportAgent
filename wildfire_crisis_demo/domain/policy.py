"""Policy constraints and enforcement rules."""
from __future__ import annotations

from .models import (
    CrisisActionBrief,
    ResourcePlan,
    SitRep,
    SupervisorReview,
    IncidentSnapshot,
)

BLOCKED_KEYWORDS: list[str] = [
    "target",
    "weapon",
    "kill",
    "lethal",
    "classified",
    "strike",
    "engage enemy",
]

MIN_CONFIDENCE_THRESHOLD: int = 20


def check_blocked_content(text: str) -> list[str]:
    """Return list of policy violations found in text."""
    violations: list[str] = []
    lower = text.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in lower:
            violations.append(f"BLOCKED_KEYWORD: '{kw}' found in output")
    return violations


def check_confidence_floor(confidence: int, stage: str) -> list[str]:
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        return [f"{stage} confidence {confidence} below minimum {MIN_CONFIDENCE_THRESHOLD}"]
    return []


def check_missing_critical_fields(snapshot: IncidentSnapshot) -> list[str]:
    violations: list[str] = []
    if not snapshot.weather_summary:
        violations.append("Missing weather_summary in IncidentSnapshot")
    if snapshot.fire_size_acres <= 0:
        violations.append("fire_size_acres must be > 0")
    return violations


def enforce_supervisor_policy(
    snapshot: IncidentSnapshot,
    sitrep: SitRep,
    resource_plan: ResourcePlan,
) -> tuple[str, list[str], list[str]]:
    """Return (decision, violations, flags). Decision: APPROVE/REVISE/BLOCK."""
    violations: list[str] = []
    flags: list[str] = []

    # Check all outputs for blocked content
    for label, obj in [("sitrep", sitrep), ("resource_plan", resource_plan)]:
        text = obj.model_dump_json()
        violations.extend(check_blocked_content(text))

    # Confidence checks
    for label, conf in [
        ("snapshot", snapshot.confidence),
        ("sitrep", sitrep.confidence),
        ("resource_plan", resource_plan.confidence),
    ]:
        violations.extend(check_confidence_floor(conf, label))

    violations.extend(check_missing_critical_fields(snapshot))

    # Flags for low-but-acceptable confidence
    for label, conf in [
        ("sitrep", sitrep.confidence),
        ("resource_plan", resource_plan.confidence),
    ]:
        if MIN_CONFIDENCE_THRESHOLD <= conf < 50:
            flags.append(f"{label} confidence is low ({conf}); verify before acting")

    if snapshot.open_questions:
        flags.append(f"Unresolved questions: {', '.join(snapshot.open_questions[:3])}")

    if violations:
        decision = "BLOCK"
    elif flags:
        decision = "APPROVE"
    else:
        decision = "APPROVE"

    return decision, violations, flags
