"""Unit tests for orchestrator pipeline."""
import asyncio
import json
from pathlib import Path

import pytest

from wildfire_crisis_demo.domain.models import (
    CoordinationResponse,
    WildfireIncidentBundle,
)
from wildfire_crisis_demo.foundry.fake_client import FakeFoundryClient
from wildfire_crisis_demo.services.orchestrator import run_pipeline


@pytest.fixture
def sample_bundle() -> WildfireIncidentBundle:
    path = Path(__file__).resolve().parent.parent.parent / "sample_payloads" / "wildfire_01.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return WildfireIncidentBundle.model_validate(data)


@pytest.fixture
def fake_client() -> FakeFoundryClient:
    return FakeFoundryClient()


@pytest.mark.asyncio
async def test_pipeline_completes(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    result = await run_pipeline(sample_bundle, fake_client)
    assert isinstance(result, CoordinationResponse)
    assert result.correlation_id
    assert result.brief_markdown
    assert result.crisis_action_brief.confidence >= 0


@pytest.mark.asyncio
async def test_pipeline_has_timings(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    result = await run_pipeline(sample_bundle, fake_client)
    assert "DataIngest" in result.timings
    assert "SitRep+ResourceAllocator" in result.timings
    assert "Supervisor" in result.timings
    assert "Brief" in result.timings
    assert "total" in result.timings


@pytest.mark.asyncio
async def test_pipeline_timeline_populated(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    result = await run_pipeline(sample_bundle, fake_client)
    timeline = result.trace_timeline
    assert len(timeline) > 0
    # Should have both incident and agent execution events
    kinds = {e.kind for e in timeline}
    assert "INCIDENT" in kinds
    assert "AGENT_EXECUTION" in kinds
    # Pipeline start and end
    event_types = [e.event_type for e in timeline]
    assert "PIPELINE_START" in event_types
    assert "PIPELINE_END" in event_types


@pytest.mark.asyncio
async def test_pipeline_agent_execution_events(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    result = await run_pipeline(sample_bundle, fake_client)
    agent_events = [e for e in result.trace_timeline if e.kind == "AGENT_EXECUTION" and e.agent_name]
    agent_names = {e.agent_name for e in agent_events}
    assert "DataIngestAgent" in agent_names
    assert "SitRepAgent" in agent_names
    assert "ResourceAllocatorAgent" in agent_names
    assert "SupervisorAgent" in agent_names
    assert "BriefAgent" in agent_names


@pytest.mark.asyncio
async def test_pipeline_correlation_id_in_brief(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    cid = "test-corr-123"
    result = await run_pipeline(sample_bundle, fake_client, correlation_id=cid)
    assert result.correlation_id == cid
    assert result.crisis_action_brief.metadata["correlation_id"] == cid


@pytest.mark.asyncio
async def test_pipeline_brief_has_3_coas(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    result = await run_pipeline(sample_bundle, fake_client)
    assert len(result.crisis_action_brief.coas) == 3


@pytest.mark.asyncio
async def test_pipeline_supervisor_policy_event(sample_bundle: WildfireIncidentBundle, fake_client: FakeFoundryClient) -> None:
    result = await run_pipeline(sample_bundle, fake_client)
    policy_events = [e for e in result.trace_timeline if e.kind == "POLICY"]
    assert len(policy_events) >= 1
    assert policy_events[0].event_type == "SUPERVISOR_DECISION"
