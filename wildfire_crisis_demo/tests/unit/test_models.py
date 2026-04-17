"""Unit tests for domain models and schema validation."""
import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from wildfire_crisis_demo.domain.models import (
    CrisisActionBrief,
    COA,
    Constraints,
    IncidentSnapshot,
    ResourcePlan,
    ResourceRecommendation,
    SitRep,
    SupervisorReview,
    TraceEvent,
    WeatherUpdate,
    WildfireIncidentBundle,
)


class TestTraceEvent:
    def test_valid_trace_event(self) -> None:
        e = TraceEvent(
            timestamp_utc=datetime.now(timezone.utc),
            kind="INCIDENT",
            event_type="WIND_SHIFT",
            source="WEATHER",
            summary="Wind shifted NW",
            confidence=80,
            citations=["WEATHER-1"],
        )
        assert e.confidence == 80

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            TraceEvent(
                timestamp_utc=datetime.now(timezone.utc),
                kind="INCIDENT",
                event_type="TEST",
                source="TEST",
                summary="Test",
                confidence=101,
            )
        with pytest.raises(ValidationError):
            TraceEvent(
                timestamp_utc=datetime.now(timezone.utc),
                kind="INCIDENT",
                event_type="TEST",
                source="TEST",
                summary="Test",
                confidence=-1,
            )

    def test_kind_literal(self) -> None:
        with pytest.raises(ValidationError):
            TraceEvent(
                timestamp_utc=datetime.now(timezone.utc),
                kind="INVALID",
                event_type="TEST",
                source="TEST",
                summary="Test",
            )

    def test_agent_execution_confidence_none_allowed(self) -> None:
        e = TraceEvent(
            timestamp_utc=datetime.now(timezone.utc),
            kind="AGENT_EXECUTION",
            event_type="AGENT_START",
            source="AGENT",
            summary="Agent started",
            confidence=None,
        )
        assert e.confidence is None

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            TraceEvent(
                timestamp_utc=datetime.now(timezone.utc),
                kind="INCIDENT",
                event_type="TEST",
                source="TEST",
                summary="Test",
                bogus_field="nope",
            )


class TestIncidentSnapshot:
    def test_valid_snapshot(self) -> None:
        s = IncidentSnapshot(
            incident_name="Test Fire",
            timestamp_utc=datetime.now(timezone.utc),
            fire_size_acres=100.0,
            containment_pct=10.0,
            weather_summary="Hot and dry",
            active_evacuations=["Zone A"],
            road_closures_active=["SR-45"],
            shelter_occupancy_pct=50.0,
            utility_disruptions=[],
            aqi_max=150,
            key_risks=["Wind shift"],
            open_questions=["ETA?"],
            confidence=75,
            assumptions=["Forecast accurate"],
            citations=["WEATHER-1"],
            verification_flags=["Check perimeter data"],
        )
        assert s.confidence == 75

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            IncidentSnapshot(
                incident_name="Test",
                timestamp_utc=datetime.now(timezone.utc),
                fire_size_acres=100.0,
                containment_pct=10.0,
                weather_summary="Hot",
                active_evacuations=[],
                road_closures_active=[],
                shelter_occupancy_pct=0.0,
                utility_disruptions=[],
                aqi_max=50,
                key_risks=[],
                open_questions=[],
                confidence=150,
                assumptions=[],
                citations=[],
                verification_flags=[],
            )


class TestSupervisorReview:
    def test_valid_decisions(self) -> None:
        for decision in ["APPROVE", "REVISE", "BLOCK"]:
            r = SupervisorReview(
                decision=decision,
                policy_violations=[],
                flags=[],
                reviewed_stages=["DataIngest"],
                confidence=80,
                assumptions=[],
                citations=[],
                verification_flags=[],
            )
            assert r.decision == decision

    def test_invalid_decision(self) -> None:
        with pytest.raises(ValidationError):
            SupervisorReview(
                decision="MAYBE",
                policy_violations=[],
                flags=[],
                reviewed_stages=[],
                confidence=80,
                assumptions=[],
                citations=[],
                verification_flags=[],
            )


class TestCOA:
    def test_coa_confidence_bounds(self) -> None:
        coa = COA(name="A", description="D", tradeoffs=[], risks=[], confidence=50)
        assert coa.confidence == 50
        with pytest.raises(ValidationError):
            COA(name="A", description="D", tradeoffs=[], risks=[], confidence=200)


class TestSamplePayloadValidation:
    @pytest.mark.parametrize("filename", ["wildfire_01.json", "wildfire_02.json"])
    def test_sample_validates(self, filename: str) -> None:
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent.parent / "sample_payloads" / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        bundle = WildfireIncidentBundle.model_validate(data)
        assert bundle.incident_summary
        assert len(bundle.weather_feed) > 0
