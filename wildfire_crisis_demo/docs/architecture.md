# Wildfire Crisis Response Coordination Agent — Technical Architecture

## The Problem

During a fast-moving wildfire, an Emergency Operations Center (EOC) commander faces a compound decision-making crisis. Within minutes, they must synthesize data from dozens of independent feeds — weather stations, fire behavior models, 911 dispatch, road sensors, shelter intake, utility SCADA systems, resource tracking — and produce actionable decisions under extreme time pressure.

Three systemic failures recur in real-world crisis coordination:

### 1. Information Overload → Decision Paralysis

Raw data arrives from disparate sources in incompatible formats and at different cadences. A weather update every 15 minutes. Fire perimeter data every hour. 911 calls in real-time. Shelter occupancy via manual headcount. No single human can normalize, cross-reference, and prioritize this volume of heterogeneous data while simultaneously making resource allocation decisions. The result: delayed decisions, missed correlations (e.g., a PSPS power shutoff degrades cell coverage in the exact zone that needs evacuation alerts), and cognitive overload at the worst possible moment.

### 2. Unstructured Recommendations → Unverifiable Decisions

When staff produce situation reports and resource recommendations, they typically arrive as free-text narratives. There is no consistent structure for confidence levels, assumptions, or citations back to source data. A commander cannot quickly distinguish a high-confidence recommendation backed by three corroborating data sources from a speculative guess based on a single unverified report. Post-incident reviews struggle to reconstruct the decision chain.

### 3. No Guardrails → Unsafe or Unverifiable Outputs

In high-stress environments, recommendations can drift into unsafe territory — overcommitting fatigued crews beyond duty hour limits, ignoring road closures in routing, or producing public messaging that causes panic. Without automated policy enforcement, these errors propagate silently.

---

## How This System Solves It

This application implements a **multi-agent coordination pipeline** using Azure AI Foundry Agent Service. Instead of one monolithic AI system, it decomposes the crisis coordination workflow into five specialized agents, each with a single responsibility, strict schema contracts, and policy guardrails. The architecture mirrors how a well-run EOC actually operates — separate desks for intelligence, operations, planning, safety, and command — but executes in seconds rather than hours.

### Architecture: Staged Pipeline with Parallel Execution

```
                        ┌──────────────────────┐
                        │  WildfireIncidentBundle │ (structured input)
                        └──────────┬───────────┘
                                   │
                    ┌──────────────▼──────────────┐
          Stage 1   │     DataIngestAgent          │  Normalize → IncidentSnapshot
                    │     (Sense)                  │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
          Stage 2   │  ┌─────────┐  ┌────────────┐│
                    │  │ SitRep  │  │ Resource   ││  asyncio.gather (parallel)
                    │  │ Agent   │  │ Allocator  ││
                    │  └────┬────┘  └─────┬──────┘│
                    └───────┼─────────────┼───────┘
                            │             │
                    ┌───────▼─────────────▼───────┐
          Stage 3   │     SupervisorAgent          │  Policy check → APPROVE / BLOCK
                    │     (Verify)                 │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
          Stage 4   │     BriefAgent               │  → CrisisActionBrief
                    │     (Decide)                 │
                    └──────────────┬───────────────┘
                                   │
                        ┌──────────▼───────────┐
                        │  CoordinationResponse  │
                        │  + Trace Timeline      │
                        └────────────────────────┘
```

### Agent Responsibilities

| Agent | Role | Input | Output | Why It's Separate |
|-------|------|-------|--------|-------------------|
| **DataIngestAgent** | Normalize heterogeneous feeds into a single structured snapshot | Raw `WildfireIncidentBundle` (weather, fire, 911, roads, shelters, utilities, resources, AQI) | `IncidentSnapshot` — unified picture with key risks and open questions | Decouples data normalization from analysis. Different data sources can change formats without affecting downstream agents. |
| **SitRepAgent** | Produce a structured situation report with priorities | `IncidentSnapshot` | `SitRep` — key facts, priorities, weather outlook, community impact, fire behavior trend | Separates intelligence analysis from resource planning. Can be reviewed independently. |
| **ResourceAllocatorAgent** | Recommend resource moves under constraints | `IncidentSnapshot` + `Constraints` | `ResourcePlan` — specific recommendations with priority, rationale, ETAs, unmet needs, constraint warnings | Resource optimization is a distinct problem from situational awareness. Constraints (duty hours, road closures, staging capacity) require dedicated reasoning. |
| **SupervisorAgent** | Enforce policy, flag uncertainty, approve or block | All upstream outputs + policy flags | `SupervisorReview` — decision (APPROVE/REVISE/BLOCK), violations, flags | **Maker-checker pattern.** No agent's output reaches the commander without review. This is the safety layer. |
| **BriefAgent** | Synthesize everything into a decision-ready brief | All reviewed outputs | `CrisisActionBrief` — overview, ranked risks, 3 COAs with tradeoffs, resource summary, public message, verification checklist | The commander needs one document, not four. This agent performs the synthesis and produces both internal and public-facing messaging. |

### Key Design Decisions and How They Address the Problem

#### 1. Strict Pydantic v2 Schemas at Every Stage Boundary

Every agent must output JSON that passes Pydantic v2 validation with `extra="forbid"`. No free-text narratives. Every output includes:

- `confidence: int` (0–100) — quantified certainty
- `assumptions: list[str]` — what the agent assumed to be true
- `citations: list[str]` — which input feed items were used (e.g., `"WEATHER-2"`, `"ROAD-1"`)
- `verification_flags: list[str]` — what a human should double-check

This directly solves Problem #2. A commander can immediately see that a resource recommendation has confidence 68, assumes road SR-45 remains closed, is based on data items RES-1 and SHELTER-1, and has a verification flag to "confirm generator fuel level before deployment." That's auditable, comparable, and actionable.

If an agent returns invalid JSON, the orchestrator performs exactly one repair attempt with a structured repair prompt. If the repair also fails, the pipeline fails fast and records an error event in the trace timeline. No silent fallbacks.

#### 2. Parallel Execution Where Dependencies Allow

SitRepAgent and ResourceAllocatorAgent run concurrently via `asyncio.gather`. They share the same input (IncidentSnapshot) but perform independent analysis. This reduces total pipeline latency and models the real-world pattern where intelligence and operations desks work simultaneously.

The orchestrator enforces the dependency graph: Stage 1 must complete before Stage 2 begins. Stage 2 must complete before Stage 3 (Supervisor) can review. Stage 3 must approve before Stage 4 (Brief) executes.

#### 3. Supervisor as Maker-Checker Gate

The SupervisorAgent implements a dual-layer review:

**Layer 1 — Local policy engine** (deterministic, no LLM): Scans all outputs for blocked keywords (weapons, targeting, PII indicators), enforces confidence floor (below 20 = automatic block), checks for missing critical fields (e.g., empty weather summary). This runs before the Foundry agent call and catches obvious violations instantly.

**Layer 2 — Foundry supervisor agent** (LLM-based): Reviews all upstream outputs for semantic policy compliance, logical consistency, and safety. Can APPROVE (with optional flags), REVISE (with instructions — enables a regeneration loop), or BLOCK (pipeline stops, error recorded).

This directly solves Problem #3. The supervisor is a structural guarantee, not an afterthought.

#### 4. Trace Timeline — Full Audit Trail

Every pipeline run produces an append-only list of `TraceEvent` objects capturing two interleaved timelines:

- **Incident events**: What happened in the world — wind shifts, evacuations, road closures, shelter status changes. Extracted from the input bundle at pipeline start.
- **Agent execution events**: What the system did — agent start/end with duration, repair attempts, supervisor decisions, pipeline completion. Recorded by the orchestrator as agents execute.

Each event has a timestamp, source classification, and optional confidence/citations. The trace timeline is:

- Returned in the API response for every run
- Stored in an in-memory TTL cache keyed by correlation_id (retrievable via `GET /crisis/trace/{id}`)
- Downloadable as JSON from the UI
- Filterable in the UI by event kind (incident vs. agent) and source (WEATHER, 911, AGENT, etc.)

This provides the post-incident reconstructability that Problem #2 lacks: you can trace exactly which data items led to which recommendations, how long each agent took, and whether the supervisor flagged anything.

#### 5. Correlation ID + Structured Logging

Every pipeline run gets a UUID correlation_id. All log entries, timeline events, and the final brief embed this ID. Combined with optional OpenTelemetry export to Azure Application Insights, this enables distributed tracing from the HTTP request through each Foundry agent/thread/run call to the final response.

---

## Technology Stack and Integration Points

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent runtime | Azure AI Foundry Agent Service (`azure-ai-projects` SDK) | Each agent is a Foundry agent with its own system prompt. The SDK handles agent creation, thread management, and run execution. Auth via `DefaultAzureCredential` (Azure CLI for local dev). |
| Schema enforcement | Pydantic v2 (strict mode, `extra="forbid"`) | Compile-time type safety + runtime validation at every stage boundary. |
| Orchestration | Python `asyncio` | Pipeline staging, parallel execution, structured error handling. No external workflow engine needed. |
| API | FastAPI | Single `POST /crisis/coordinate` endpoint. Returns structured JSON + rendered Markdown. |
| Observability | Python `logging` (JSON format) + optional OpenTelemetry → Azure Monitor | Structured logs with correlation context. Optional distributed tracing. |
| Offline testing | `FakeFoundryClient` | Returns deterministic JSON for each agent. All unit and contract tests run without Azure. |
| UI | Vanilla HTML/CSS/JS | Single page, no framework. Dark theme. Sample payload loader, simulate-update button, timeline panel. Booth-demo ready. |

### Foundry Client Abstraction

The system uses a `FoundryClientBase` abstract class with two implementations:

- `AzureFoundryClient`: Creates a real Foundry agent per call, creates a thread, posts the user message, runs the agent, extracts the assistant response, then deletes the agent. This is the "real" path.
- `FakeFoundryClient`: Returns hardcoded deterministic JSON matching each agent's schema. Used for tests and demos without Azure credentials.

Dependency injection (`app/deps.py`) selects the implementation based on whether `AZURE_AI_PROJECT_ENDPOINT` is set in the environment.

---

## What the Demo Actually Shows

For a 2–4 minute trade show demo, this system demonstrates five capabilities:

1. **Multi-agent collaboration** — Five specialized agents with distinct prompts and schemas, executing in a staged pipeline with parallel execution where possible. The Trace Timeline's "Agent Execution" tab makes the orchestration pattern visible.

2. **Real-time data ingestion** — The "Simulate Update" button mutates the input payload (wind shift, fire growth, AQI increase, shelter occupancy rise), modeling what a live feed integration would produce. Each run processes the latest state.

3. **Decision support workflow** — The Crisis Action Brief provides three Courses of Action with confidence scores, tradeoffs, and risks. The verification checklist and "DECISION SUPPORT ONLY" badge reinforce that this assists human judgment rather than replacing it.

4. **Guardrails and traceability** — The supervisor gate, blocked-keyword detection, confidence floors, and per-recommendation citations demonstrate that AI outputs are auditable and policy-constrained. The Trace Timeline provides the full audit trail.

5. **Observability** — Stage timings in the response, structured logging with correlation IDs, and the Trace Timeline panel show operational visibility into the AI system's behavior.

---

## Limitations and Scope

- **Synthetic data only.** All scenarios use fictional locations, no PII, no classified information.
- **Decision support only.** The system explicitly does not issue orders, claim command authority, or automate any real-world action.
- **No persistent storage.** Timeline data is in-memory with a 1-hour TTL. This is a demo, not a production system.
- **Single-turn agents.** Each agent runs once per pipeline stage (with one repair retry). There is no multi-turn conversation or iterative refinement loop (beyond the supervisor's REVISE capability).
- **No real data feeds.** In production, the `WildfireIncidentBundle` would be assembled by data integration services pulling from weather APIs, CAD systems, GIS layers, and SCADA. This demo accepts pre-built or simulated payloads.
