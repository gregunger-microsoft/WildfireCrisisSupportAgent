"""Unit tests for policy enforcement."""
import pytest

from wildfire_crisis_demo.domain.policy import (
    check_blocked_content,
    check_confidence_floor,
    enforce_supervisor_policy,
)
from wildfire_crisis_demo.domain.models import IncidentSnapshot, SitRep, ResourcePlan
from datetime import datetime, timezone


def _make_snapshot(**overrides) -> IncidentSnapshot:
    defaults = dict(
        incident_name="Test", timestamp_utc=datetime.now(timezone.utc),
        fire_size_acres=100.0, containment_pct=10.0, weather_summary="Hot",
        active_evacuations=[], road_closures_active=[], shelter_occupancy_pct=50.0,
        utility_disruptions=[], aqi_max=150, key_risks=[], open_questions=[],
        confidence=75, assumptions=[], citations=["W-1"], verification_flags=[],
    )
    defaults.update(overrides)
    return IncidentSnapshot(**defaults)


def _make_sitrep(**overrides) -> SitRep:
    defaults = dict(
        period="test", situation_summary="Test", key_facts=["a"], priorities=["b"],
        open_questions=[], weather_outlook="Clear", fire_behavior_trend="STABLE",
        community_impact="None", confidence=70, assumptions=[], citations=["W-1"],
        verification_flags=[],
    )
    defaults.update(overrides)
    return SitRep(**defaults)


def _make_resource_plan(**overrides) -> ResourcePlan:
    defaults = dict(
        recommendations=[], unmet_needs=[], constraint_warnings=[],
        confidence=65, assumptions=[], citations=["R-1"], verification_flags=[],
    )
    defaults.update(overrides)
    return ResourcePlan(**defaults)


class TestBlockedContent:
    def test_detects_blocked_keywords(self) -> None:
        violations = check_blocked_content("We should target the enemy")
        assert len(violations) == 1
        assert any("target" in v for v in violations)

    def test_clean_content(self) -> None:
        assert check_blocked_content("Deploy engine to Zone A") == []


class TestConfidenceFloor:
    def test_below_threshold(self) -> None:
        assert len(check_confidence_floor(10, "test")) == 1

    def test_at_threshold(self) -> None:
        assert check_confidence_floor(20, "test") == []


class TestEnforceSupervisorPolicy:
    def test_approve_normal(self) -> None:
        decision, violations, flags = enforce_supervisor_policy(
            _make_snapshot(), _make_sitrep(), _make_resource_plan()
        )
        assert decision == "APPROVE"
        assert violations == []

    def test_block_low_confidence(self) -> None:
        decision, violations, flags = enforce_supervisor_policy(
            _make_snapshot(confidence=5), _make_sitrep(), _make_resource_plan()
        )
        assert decision == "BLOCK"
        assert any("confidence" in v for v in violations)

    def test_block_missing_weather(self) -> None:
        decision, violations, _ = enforce_supervisor_policy(
            _make_snapshot(weather_summary=""), _make_sitrep(), _make_resource_plan()
        )
        assert decision == "BLOCK"

    def test_flags_low_confidence(self) -> None:
        decision, _, flags = enforce_supervisor_policy(
            _make_snapshot(), _make_sitrep(confidence=35), _make_resource_plan()
        )
        assert decision == "APPROVE"
        assert any("low" in f for f in flags)
