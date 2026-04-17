"""Contract tests: each fake agent output validates against its schema."""
import json

import pytest

from wildfire_crisis_demo.domain.models import (
    CrisisActionBrief,
    IncidentSnapshot,
    ResourcePlan,
    SitRep,
    SupervisorReview,
)
from wildfire_crisis_demo.foundry.fake_client import FakeFoundryClient


@pytest.fixture
def fake_client() -> FakeFoundryClient:
    return FakeFoundryClient()


@pytest.mark.asyncio
async def test_data_ingest_schema(fake_client: FakeFoundryClient) -> None:
    raw = await fake_client.run_agent("DataIngestAgent", "", "")
    data = json.loads(raw)
    snapshot = IncidentSnapshot.model_validate(data)
    assert 0 <= snapshot.confidence <= 100
    assert len(snapshot.citations) > 0


@pytest.mark.asyncio
async def test_sitrep_schema(fake_client: FakeFoundryClient) -> None:
    raw = await fake_client.run_agent("SitRepAgent", "", "")
    data = json.loads(raw)
    sitrep = SitRep.model_validate(data)
    assert sitrep.fire_behavior_trend in ("INCREASING", "STABLE", "DECREASING")


@pytest.mark.asyncio
async def test_resource_plan_schema(fake_client: FakeFoundryClient) -> None:
    raw = await fake_client.run_agent("ResourceAllocatorAgent", "", "")
    data = json.loads(raw)
    plan = ResourcePlan.model_validate(data)
    assert all(r.priority in ("LOW", "MEDIUM", "HIGH", "CRITICAL") for r in plan.recommendations)


@pytest.mark.asyncio
async def test_supervisor_schema(fake_client: FakeFoundryClient) -> None:
    raw = await fake_client.run_agent("SupervisorAgent", "", "")
    data = json.loads(raw)
    review = SupervisorReview.model_validate(data)
    assert review.decision in ("APPROVE", "REVISE", "BLOCK")


@pytest.mark.asyncio
async def test_brief_schema(fake_client: FakeFoundryClient) -> None:
    raw = await fake_client.run_agent("BriefAgent", "", "")
    data = json.loads(raw)
    brief = CrisisActionBrief.model_validate(data)
    assert len(brief.coas) == 3
    assert brief.public_message
    assert brief.internal_message
