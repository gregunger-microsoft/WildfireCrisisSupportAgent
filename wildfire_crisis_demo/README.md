# 🔥 Wildfire Crisis Response Coordination Agent

Multi-agent decision support system for wildfire crisis coordination, built with Azure AI Foundry Agent Service.

> **⚠️ DECISION SUPPORT ONLY** — This system provides recommendations, not command authority.  
> **All data is synthetic/fictional.** No PII. No classified information.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                       │
│  correlation_id + Trace Timeline                     │
├──────┬──────────────────────────────┬───────────────┤
│ S1   │ DataIngestAgent (Sense)      │ → Snapshot    │
├──────┼──────────┬───────────────────┤               │
│ S2   │ SitRep   │ ResourceAllocator │ → parallel    │
├──────┼──────────┴───────────────────┤               │
│ S3   │ SupervisorAgent (Verify)     │ → approve/block│
├──────┼──────────────────────────────┤               │
│ S4   │ BriefAgent (Decide)          │ → Brief + MD  │
└──────┴──────────────────────────────┴───────────────┘
```

## Quick Start

### 1. Setup

```bash
cd wildfire_crisis_demo
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your Azure AI Foundry endpoint (optional for local/fake mode)
```

**Without Azure credentials**, the system uses `FakeFoundryClient` with deterministic responses — perfect for demos and testing.

**With Azure credentials**, set `AZURE_AI_PROJECT_ENDPOINT` and login:
```bash
az login
```

### 3. Run FastAPI Server

```bash
uvicorn wildfire_crisis_demo.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000

### 4. Run CLI

```bash
python -m wildfire_crisis_demo.cli sample_payloads/wildfire_01.json
```

### 5. Run Tests

```bash
# All offline tests (unit + contract)
pytest tests/ -v

# Integration tests (requires Azure)
AZURE_AI_PROJECT_ENDPOINT=https://... pytest tests/integration/ -v
```

### 6. curl Examples

```bash
# Get sample payload
curl http://localhost:8000/api/samples/wildfire_01

# Run coordination
curl -X POST http://localhost:8000/crisis/coordinate \
  -H "Content-Type: application/json" \
  -d @sample_payloads/wildfire_01.json

# Get trace (after a run, use the correlation_id from the response)
curl http://localhost:8000/crisis/trace/{correlation_id}
```

## Env Vars (.env)

| Variable | Required | Description |
|---|---|---|
| `AZURE_AI_PROJECT_ENDPOINT` | No | Azure AI Foundry project endpoint. If unset, uses FakeFoundryClient |
| `AZURE_AI_MODEL` | No | Model name (default: `gpt-4o`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No | Enables OpenTelemetry export to App Insights |

## Observability & Tracing

- **Structured JSON logging** with `correlation_id`, `stage_name`, `agent_name`, `duration_ms`
- **Trace Timeline**: every run produces an append-only timeline of incident events + agent execution events
- **Optional Azure Monitor**: if `APPLICATIONINSIGHTS_CONNECTION_STRING` is set, OpenTelemetry spans are exported to Application Insights
- **Foundry integration**: Azure AI Foundry provides built-in tracing for agent/thread/run operations. When using the real client, these traces appear in the Foundry portal alongside your App Insights data, giving end-to-end visibility from API call → agent execution → model inference.

## 2-Minute Booth Demo Script

1. **Open the UI** at `http://localhost:8000` — point out the dark theme, "DECISION SUPPORT ONLY" badge
2. **Load Scenario 1** from the dropdown — show the JSON payload with weather, fire, evacuation, road closures, shelters, utilities, resources
3. **Click "Simulate Update"** — watch wind speed increase, fire grow, AQI spike — "real-time data ingestion"
4. **Click "Run Coordination"** — watch the spinner, then results appear:
   - **Crisis Action Brief** — situation overview, ranked risks, 3 COAs with tradeoffs
   - **Public message** — ready to publish, no PII, no panic
   - **Verification checklist** — "human-in-the-loop, every recommendation needs verification"
5. **Show Trace Timeline** — switch between "Incident Events" and "Agent Execution" tabs:
   - Incident tab: weather updates, fire behavior, evacuations, road closures — "what happened"
   - Agent tab: PIPELINE_START → DataIngest → SitRep/ResourceAllocator (parallel) → Supervisor → Brief → PIPELINE_END — "what the system did"
   - Filter by source — show WEATHER events, then AGENT events
   - Click a row to expand details and citations
6. **Download trace_timeline.json** — "full audit trail for every run"
7. **Highlight key points**:
   - "5 specialized agents, each with its own system prompt and schema"
   - "Supervisor enforces policy — blocks unsafe outputs"
   - "Every output has confidence scores, assumptions, citations, verification flags"
   - "Parallel execution of SitRep + ResourceAllocator"
   - "All synthetic data — no PII, no classified info"

## Guardrails

- No weapons guidance, targeting, or harmful instructions
- No PII in any output
- Every recommendation includes confidence (0-100), assumptions, citations, verification flags
- SupervisorAgent enforces policy constraints and blocks unsafe outputs
- Blocked keywords detected and rejected
- One repair attempt for invalid JSON; then fail fast

## Project Structure

```
wildfire_crisis_demo/
  app/main.py          — FastAPI entry point
  app/routes.py        — API routes
  app/deps.py          — dependency injection
  domain/models.py     — Pydantic v2 schemas
  domain/policy.py     — policy enforcement
  services/orchestrator.py — pipeline orchestration
  services/prompts.py  — agent system prompts
  services/simulator.py — simulate update logic
  services/timeline.py — trace timeline store
  foundry/client.py    — Azure Foundry client
  foundry/fake_client.py — deterministic fake
  ui/index.html        — single-page UI
  ui/render.py         — markdown rendering
  sample_payloads/     — synthetic test data
  cli.py               — CLI runner
  observability.py     — logging + OTel
  tests/               — unit, contract, integration
```
