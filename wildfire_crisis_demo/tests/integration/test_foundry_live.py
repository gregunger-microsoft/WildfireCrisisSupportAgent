"""Integration tests — skipped if Azure credentials/endpoint not configured."""
import json
import os
from pathlib import Path

import pytest

SKIP_REASON = "AZURE_AI_PROJECT_ENDPOINT not set"
pytestmark = pytest.mark.skipif(
    not os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
    reason=SKIP_REASON,
)


@pytest.fixture
def sample_bundle():
    from wildfire_crisis_demo.domain.models import WildfireIncidentBundle
    path = Path(__file__).resolve().parent.parent.parent / "sample_payloads" / "wildfire_01.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return WildfireIncidentBundle.model_validate(data)


@pytest.mark.asyncio
async def test_real_foundry_pipeline(sample_bundle) -> None:
    from wildfire_crisis_demo.foundry.client import AzureFoundryClient
    from wildfire_crisis_demo.services.orchestrator import run_pipeline

    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model = os.environ.get("AZURE_AI_MODEL", "gpt-4o")
    client = AzureFoundryClient(endpoint=endpoint, model=model)
    result = await run_pipeline(sample_bundle, client)
    assert result.correlation_id
    assert result.crisis_action_brief.confidence >= 0
    assert len(result.trace_timeline) > 0
