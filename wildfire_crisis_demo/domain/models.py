"""Pydantic v2 domain models for Wildfire Crisis Response Coordination."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── Input Feed Models ──────────────────────────────────────────────────────

class WeatherUpdate(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    temperature_f: float
    humidity_pct: float
    wind_speed_mph: float
    wind_direction: str
    wind_gust_mph: Optional[float] = None
    red_flag_warning: bool = False
    summary: str


class FireBehaviorUpdate(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    perimeter_acres: float
    rate_of_spread_chains_per_hour: float
    containment_pct: float
    flame_length_ft: Optional[float] = None
    spot_fire_count: int = 0
    summary: str


class IncidentUpdate(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    event_type: str
    location: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    summary: str


class RoadClosure(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    road_name: str
    segment: str
    status: Literal["CLOSED", "RESTRICTED", "OPEN"]
    reason: str
    detour_available: bool = False


class EvacuationUpdate(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    zone_name: str
    order_level: Literal["ADVISORY", "WARNING", "ORDER"]
    population_affected: int
    summary: str


class ShelterStatus(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    name: str
    location: str
    capacity: int
    current_occupancy: int
    has_power: bool = True
    has_medical: bool = False
    pet_friendly: bool = False
    ada_accessible: bool = True
    summary: str


class UtilityUpdate(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    utility_type: Literal["POWER", "WATER", "COMMS", "GAS"]
    status: Literal["NORMAL", "DEGRADED", "SHUTOFF"]
    affected_area: str
    estimated_restoration_utc: Optional[datetime] = None
    summary: str


class ResourceStatus(BaseModel, extra="forbid"):
    id: str
    resource_type: Literal[
        "ENGINE", "HAND_CREW", "AIR_TANKER", "HELICOPTER",
        "AMBULANCE", "BUS", "GENERATOR", "WATER_TENDER",
    ]
    unit_name: str
    status: Literal["AVAILABLE", "ASSIGNED", "EN_ROUTE", "OUT_OF_SERVICE"]
    location: str
    eta_minutes: Optional[int] = None
    duty_hours_remaining: Optional[float] = None
    summary: str


class AirQualityUpdate(BaseModel, extra="forbid"):
    id: str
    timestamp_utc: datetime
    aqi: int
    pm25: float
    location: str
    health_advisory: str
    summary: str


class Constraints(BaseModel, extra="forbid"):
    max_crew_duty_hours: float = 16.0
    staging_capacity: int = 50
    air_support_window_start_utc: Optional[datetime] = None
    air_support_window_end_utc: Optional[datetime] = None
    max_evacuation_buses: int = 20
    mutual_aid_available: bool = True
    road_closure_ids: list[str] = Field(default_factory=list)


class WildfireIncidentBundle(BaseModel, extra="forbid"):
    incident_summary: str
    weather_feed: list[WeatherUpdate]
    fire_behavior: list[FireBehaviorUpdate]
    incident_feed: list[IncidentUpdate]
    road_closures: list[RoadClosure]
    evacuation: list[EvacuationUpdate]
    shelters: list[ShelterStatus]
    utilities: list[UtilityUpdate]
    resources: list[ResourceStatus]
    constraints: Constraints
    air_quality: list[AirQualityUpdate]


# ── Trace Timeline ─────────────────────────────────────────────────────────

class TraceEvent(BaseModel, extra="forbid"):
    timestamp_utc: datetime
    kind: Literal["INCIDENT", "AGENT_EXECUTION", "POLICY", "ERROR"]
    event_type: str
    source: str
    summary: str
    confidence: Optional[int] = Field(default=None, ge=0, le=100)
    citations: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)
    stage_name: Optional[str] = None
    agent_name: Optional[str] = None
    duration_ms: Optional[int] = None
    status: Optional[Literal["ok", "retry", "blocked", "failed"]] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


# ── Agent Output Schemas ───────────────────────────────────────────────────

class _AgentOutputBase(BaseModel, extra="forbid"):
    confidence: int = Field(ge=0, le=100)
    assumptions: list[str]
    citations: list[str]
    verification_flags: list[str]


class IncidentSnapshot(_AgentOutputBase):
    incident_name: str
    timestamp_utc: datetime
    fire_size_acres: float
    containment_pct: float
    weather_summary: str
    active_evacuations: list[str]
    road_closures_active: list[str]
    shelter_occupancy_pct: float
    utility_disruptions: list[str]
    aqi_max: int
    key_risks: list[str]
    open_questions: list[str]


class SitRep(_AgentOutputBase):
    period: str
    situation_summary: str
    key_facts: list[str]
    priorities: list[str]
    open_questions: list[str]
    weather_outlook: str
    fire_behavior_trend: Literal["INCREASING", "STABLE", "DECREASING"]
    community_impact: str


class ResourceRecommendation(BaseModel, extra="forbid"):
    resource_id: str
    resource_type: str
    action: str
    destination: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    rationale: str
    eta_minutes: Optional[int] = None


class ResourcePlan(_AgentOutputBase):
    recommendations: list[ResourceRecommendation]
    unmet_needs: list[str]
    constraint_warnings: list[str]


class SupervisorReview(_AgentOutputBase):
    decision: Literal["APPROVE", "REVISE", "BLOCK"]
    policy_violations: list[str]
    revision_instructions: Optional[str] = None
    flags: list[str]
    reviewed_stages: list[str]


class COA(BaseModel, extra="forbid"):
    name: str
    description: str
    tradeoffs: list[str]
    risks: list[str]
    confidence: int = Field(ge=0, le=100)


class CrisisActionBrief(_AgentOutputBase):
    overview: str
    risks: list[dict]
    coas: list[COA]
    resource_plan_summary: str
    verification_checklist: list[str]
    public_message: str
    internal_message: str
    metadata: dict


# ── API Response ───────────────────────────────────────────────────────────

class CoordinationResponse(BaseModel):
    crisis_action_brief: CrisisActionBrief
    brief_markdown: str
    timings: dict[str, float]
    correlation_id: str
    trace_timeline: list[TraceEvent]
