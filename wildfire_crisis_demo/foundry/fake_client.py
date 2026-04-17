"""Deterministic fake Foundry client for offline testing."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .client import FoundryClientBase


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_FAKE_RESPONSES: dict[str, dict] = {
    "DataIngestAgent": {
        "incident_name": "Ponderosa County Wildfire",
        "timestamp_utc": _now_iso(),
        "fire_size_acres": 2500.0,
        "containment_pct": 15.0,
        "weather_summary": "Hot, dry, winds 25 mph gusting 40 from SW. Red flag warning active.",
        "active_evacuations": ["Zone A - mandatory", "Zone B - advisory"],
        "road_closures_active": ["SR-45 mile 12-18", "County Rd 7"],
        "shelter_occupancy_pct": 62.0,
        "utility_disruptions": ["PSPS Zone C - power shutoff", "Cell tower degraded sector 4"],
        "aqi_max": 285,
        "key_risks": [
            "Wind shift expected 1800h may push fire toward Zone C",
            "Shelter capacity nearing limit",
            "Air tanker window closes at 1900h",
        ],
        "open_questions": [
            "Mutual aid ETA from neighboring county?",
            "Generator fuel resupply status?",
        ],
        "confidence": 78,
        "assumptions": [
            "Weather forecast accuracy +/- 2 hours",
            "Perimeter data from 1 hour ago",
        ],
        "citations": ["WEATHER-1", "WEATHER-2", "FIRE-1", "EVAC-1", "ROAD-1", "SHELTER-1", "UTIL-1"],
        "verification_flags": ["Perimeter data may be stale", "AQI sensor coverage limited"],
    },
    "SitRepAgent": {
        "period": "2025-08-15T1200Z to 2025-08-15T1800Z",
        "situation_summary": "Fast-moving wildfire in Ponderosa County. 2500 acres, 15% contained. Mandatory evacuation Zone A, advisory Zone B. Wind shift expected 1800h threatens Zone C.",
        "key_facts": [
            "Fire size: 2500 acres, 15% contained",
            "Rate of spread: 300 chains/hour",
            "2 road closures affecting evacuation routes",
            "Shelter at 62% capacity",
            "AQI 285 - Very Unhealthy",
            "PSPS active in Zone C",
        ],
        "priorities": [
            "Prepare Zone C evacuation contingency",
            "Secure additional shelter capacity",
            "Position resources for wind shift",
            "Address medical needs at shelters",
        ],
        "open_questions": [
            "Mutual aid response timeline?",
            "Generator fuel resupply ETA?",
            "Cell coverage restoration plan?",
        ],
        "weather_outlook": "SW winds 25-40 mph until 1800h, then shifting NW 15-25 mph. Humidity rising to 25% overnight.",
        "fire_behavior_trend": "INCREASING",
        "community_impact": "Approximately 3200 residents affected. 2 schools closed. Highway 45 closed impacting commuters. Air quality hazardous.",
        "confidence": 72,
        "assumptions": [
            "Weather models agree on wind shift timing +/- 2h",
            "Current resource positions accurate as of last check-in",
        ],
        "citations": ["WEATHER-1", "WEATHER-2", "FIRE-1", "EVAC-1", "EVAC-2", "SHELTER-1", "AQ-1"],
        "verification_flags": ["Wind shift timing uncertain", "Spot fire reports unconfirmed"],
    },
    "ResourceAllocatorAgent": {
        "recommendations": [
            {
                "resource_id": "ENG-3",
                "resource_type": "ENGINE",
                "action": "Reposition to Zone C staging area",
                "destination": "Zone C Staging - Hwy 12 / Pine Rd",
                "priority": "HIGH",
                "rationale": "Pre-position for potential Zone C defense if wind shifts",
                "eta_minutes": 25,
            },
            {
                "resource_id": "BUS-1",
                "resource_type": "BUS",
                "action": "Stage at Zone C for potential evacuation",
                "destination": "Zone C Community Center",
                "priority": "HIGH",
                "rationale": "Enable rapid evacuation if Zone C elevated to mandatory",
                "eta_minutes": 30,
            },
            {
                "resource_id": "GEN-2",
                "resource_type": "GENERATOR",
                "action": "Deploy to Riverside Shelter",
                "destination": "Riverside Community Shelter",
                "priority": "CRITICAL",
                "rationale": "Shelter lost power due to PSPS; medical patients on-site",
                "eta_minutes": 45,
            },
            {
                "resource_id": "AMB-1",
                "resource_type": "AMBULANCE",
                "action": "Relocate to Riverside Shelter",
                "destination": "Riverside Community Shelter",
                "priority": "MEDIUM",
                "rationale": "Medical surge support for shelter with vulnerable populations",
                "eta_minutes": 20,
            },
        ],
        "unmet_needs": [
            "1 additional hand crew for line construction SE flank",
            "Fuel resupply for generators within 4 hours",
        ],
        "constraint_warnings": [
            "Hand Crew Alpha at 14 of 16 duty hours - rotation needed by 2000h",
            "Air tanker window closes 1900h - last sortie must launch by 1830h",
        ],
        "confidence": 68,
        "assumptions": [
            "Road SR-45 remains closed; using alternate routes",
            "Zone C evacuation is contingency, not ordered yet",
            "Generator fuel sufficient for 8 hours",
        ],
        "citations": ["RES-1", "RES-2", "RES-3", "ROAD-1", "SHELTER-1", "UTIL-1"],
        "verification_flags": [
            "Verify ENG-3 availability before repositioning",
            "Confirm generator fuel level before deployment",
        ],
    },
    "SupervisorAgent": {
        "decision": "APPROVE",
        "policy_violations": [],
        "revision_instructions": None,
        "flags": [
            "Resource plan confidence 68 - verify before acting",
            "Wind shift timing uncertain - monitor closely",
            "Unresolved: Mutual aid ETA",
        ],
        "reviewed_stages": ["DataIngest", "SitRep", "ResourceAllocator"],
        "confidence": 82,
        "assumptions": ["All agent outputs validated against schema", "No blocked content detected"],
        "citations": ["WEATHER-1", "FIRE-1", "RES-1"],
        "verification_flags": ["Human review recommended before executing resource moves"],
    },
    "BriefAgent": {
        "overview": "Ponderosa County wildfire: 2500 acres, 15% contained, rapid spread. Wind shift at ~1800h threatens Zone C. Mandatory evac Zone A, advisory Zone B. Shelters at 62%. PSPS active. AQI hazardous (285).",
        "risks": [
            {"risk": "Wind shift pushes fire into Zone C", "likelihood": "HIGH", "impact": "CRITICAL", "confidence": 70},
            {"risk": "Shelter capacity exceeded", "likelihood": "MEDIUM", "impact": "HIGH", "confidence": 75},
            {"risk": "Communications degraded in PSPS area", "likelihood": "HIGH", "impact": "MEDIUM", "confidence": 80},
            {"risk": "Crew fatigue - duty hour limits approaching", "likelihood": "HIGH", "impact": "MEDIUM", "confidence": 85},
        ],
        "coas": [
            {
                "name": "COA 1: Aggressive Pre-Position",
                "description": "Pre-position engines and buses in Zone C now. Launch final air tanker sortie. Deploy generator to Riverside Shelter immediately.",
                "tradeoffs": ["Commits resources before wind shift confirmed", "Reduces reserve capacity"],
                "risks": ["If wind doesn't shift, resources out of position for 2+ hours"],
                "confidence": 72,
            },
            {
                "name": "COA 2: Staged Response",
                "description": "Stage resources at Zone C periphery. Hold air tanker. Deploy generator immediately. Trigger Zone C evac only on confirmed wind shift.",
                "tradeoffs": ["Slower response if wind shifts", "Preserves flexibility"],
                "risks": ["Delayed evacuation if wind shift is sudden"],
                "confidence": 68,
            },
            {
                "name": "COA 3: Consolidate & Defend",
                "description": "Focus on current Zone A/B operations. Strengthen shelter capacity. Request mutual aid. React to wind shift if/when confirmed.",
                "tradeoffs": ["Most conservative", "Maximizes current operations"],
                "risks": ["Zone C population at risk if wind shift is rapid", "Reactive posture"],
                "confidence": 55,
            },
        ],
        "resource_plan_summary": "4 resource moves recommended: reposition ENG-3 to Zone C, stage BUS-1 for evac, deploy GEN-2 to Riverside Shelter (critical - medical patients), relocate AMB-1 for medical surge. Unmet: 1 hand crew, generator fuel resupply.",
        "verification_checklist": [
            "Confirm ENG-3 availability and fuel status",
            "Verify Riverside Shelter medical patient count",
            "Check mutual aid response ETA",
            "Confirm air tanker sortie window with air ops",
            "Validate Zone C population count for evacuation planning",
            "Verify generator fuel resupply timeline",
        ],
        "public_message": "PONDEROSA COUNTY WILDFIRE UPDATE: A wildfire is active in the county. Zone A residents must evacuate now. Zone B residents should prepare to leave. Shelters are open at Ponderosa High School and Riverside Community Center. Air quality is unhealthy - stay indoors, close windows, use N95 masks if outside. Monitor local emergency channels for updates. Do NOT call 911 unless you have an emergency. Info line: 555-0100.",
        "internal_message": "EOC INTERNAL: Wind shift expected ~1800h may threaten Zone C. Pre-positioning recommended per COA 1 or 2. Shelter capacity concern - activate overflow plan. PSPS impacting Riverside Shelter - generator deployment critical. Hand crew rotation needed by 2000h. Air ops final window 1830h. Mutual aid status pending. Next briefing 1700h.",
        "metadata": {
            "confidence": 71,
            "correlation_id": "PLACEHOLDER",
            "generated_utc": _now_iso(),
            "citations": ["WEATHER-1", "WEATHER-2", "FIRE-1", "EVAC-1", "ROAD-1", "SHELTER-1", "UTIL-1", "AQ-1", "RES-1", "RES-2"],
        },
        "confidence": 71,
        "assumptions": [
            "All upstream agent data validated by supervisor",
            "Weather forecast window +/- 2 hours",
            "Resource positions current as of last check-in",
        ],
        "citations": ["WEATHER-1", "WEATHER-2", "FIRE-1", "EVAC-1", "ROAD-1", "SHELTER-1", "UTIL-1", "AQ-1"],
        "verification_flags": [
            "Wind shift timing uncertain - COA selection depends on confirmation",
            "Human decision required on COA selection",
            "Resource moves are RECOMMENDATIONS only",
        ],
    },
}


class FakeFoundryClient(FoundryClientBase):
    """Returns deterministic JSON for each agent. No Azure required."""

    async def run_agent(
        self,
        agent_name: str,
        system_prompt: str,
        user_message: str,
    ) -> str:
        if agent_name not in _FAKE_RESPONSES:
            raise ValueError(f"No fake response for agent: {agent_name}")
        resp = _FAKE_RESPONSES[agent_name].copy()
        # Ensure fresh timestamp for DataIngest
        if agent_name == "DataIngestAgent":
            resp["timestamp_utc"] = _now_iso()
        if agent_name == "BriefAgent":
            resp["metadata"]["generated_utc"] = _now_iso()
        return json.dumps(resp)
