# Pushan — The Next-Gen AI Agriculture Engine (V0.9)

Pushan is a prototype smart-irrigation process-intelligence platform. V0.9 adds persistent human approval, deterministic guardrails, idempotent workflow automation, incident creation, notifications, and an auditable operator interface. It preserves the V0.1–V0.8 sensor, rule, ML, operational, SQLite, API, dashboard, RAG, and LangGraph layers.

## Project evolution

```text
V0.1  Rule-Based Irrigation Engine
V0.2  Sensor Simulation + Operational Feasibility
V0.3  SQLite Persistence + Historical Records
V0.4  Machine-Learning Irrigation Prediction
V0.5  FastAPI Backend
V0.6  Streamlit Dashboard
V0.7  RAG Agriculture Knowledge System
V0.8  LangGraph Agentic Orchestration
V0.9  Human Approval + Guardrails + Workflow Automation
```

V0.9 turns recommendations into controlled operational workflows. A technically feasible irrigation recommendation is not automatically authorized: guardrails can require a durable human decision, and a rejected workflow never starts.

## V0.9 safety and automation architecture

```text
Agent assessment → deterministic guardrails → workflow proposal
                                              ├─ safe → simulated execution
                                              ├─ risky → WAITING_FOR_APPROVAL
                                              │           ├─ approve → execute
                                              │           └─ reject  → BLOCKED
                                              └─ fault → incident + notification
Every transition → SQLite audit log
```

The approval pause is explicit persisted state rather than an in-memory prompt. `approval_requests` and `workflow_executions` survive API restarts, so an operator can decide later from the Approval Center. This prototype uses no unrestricted autonomous action and never controls physical equipment.

Guardrails are deterministic and run after the operational engine. Faulty sensors, an offline pump, insufficient water, operational blocks, high-risk recommendations, and irrigation volumes above 5,000 litres are handled before authorization. The API response distinguishes `technically_executable` from `authorized_to_execute`.

Workflow proposals carry an idempotency key. Repeating the same proposal reuses its existing record, and repeating a completed execution does not create another incident or notification. Simulated local notification delivery works with no external service. Setting `PUSHAN_AUTOMATION_WEBHOOK_URL` enables a bounded optional JSON webhook; failures are recorded rather than crashing the workflow.

## V0.8 controlled agent architecture

```text
User → Pushan Agent → LangGraph State → Intent Classification
                              ↓ conditional routing
                Sensor Tool | RAG Tool | ML Tool
                              ↓
                Rule Engine → Operational Engine
                              ↓
                   Final Response + Trace
```

The graph supports `FIELD_ASSESSMENT`, `KNOWLEDGE_QUERY`, and `FULL_ANALYSIS`. It extracts simple IDs such as `FIELD_001`, routes with real LangGraph conditional edges, retries failed RAG work at most twice, and continues in a reported degraded mode when optional ML or knowledge services are unavailable.

### LangGraph concepts

- **State:** shared data carrying the request, intent, field data, results, errors, retry count, trace, and final response.
- **Node:** one focused function such as classification, sensor retrieval, rules, ML, RAG, operational evaluation, or final formatting.
- **Edge:** a connection specifying the next node.
- **Conditional edge:** a branch selected from state; Pushan uses these for intent routing, missing fields, full analysis, and finite retries.
- **Tool:** a thin wrapper around an existing Pushan capability, with no duplicated business logic.
- **Orchestration:** coordinating tools and steps in the correct order.
- **Retry:** repeating failed RAG retrieval within an explicit two-attempt maximum.

A normal workflow has a mostly predetermined sequence. An agentic workflow inspects state and selects routes based on the task and current results. Pushan remains controlled agentic orchestration, not unrestricted autonomy. Its trace exposes only node/tool status—not private chain-of-thought.

```text
LLM / Agent → orchestrates and explains
ML          → predicts
Rules       → constrain
Operational Engine → decides feasibility
```

Final responses are assembled from structured state. If the operational engine blocks execution, neither RAG guidance nor an LLM can change it to “proceed.”

RAG allows Pushan to search its own agriculture documents before asking an LLM to generate an answer. This reduces reliance on model memory and makes answers traceable to the project's knowledge base.

## Architecture and responsibilities

```text
User Question → Streamlit → FastAPI → RAG Service → Retriever
     → Chroma Vector Store → Relevant Chunks → LLM
     → Grounded Answer + Source Filenames
```

The RAG path complements—never replaces—the operational path:

- **RAG:** knowledge and explanation only.
- **ML:** predictive advisory only.
- **Rule engine:** deterministic irrigation recommendation.
- **Operational engine:** execution feasibility and safety state.

The knowledge assistant cannot switch a pump or override operational rules. Streamlit calls FastAPI; it never imports backend RAG or irrigation logic directly.

## RAG concepts in plain English

- **Chunking:** breaking documents into small overlapping passages. V0.7 uses 800 characters with 100 overlap and preserves source metadata.
- **Embeddings:** numerical text representations used to find related wording. V0.7 uses deterministic local hash embeddings, so retrieval needs no paid API.
- **Vector database:** Chroma stores chunk vectors and metadata for similarity search.
- **Retrieval:** selecting the chunks most relevant to the question before generation.
- **Generation:** a Google Gemini model turns only the retrieved passages into a readable answer.
- **Grounding:** requiring the model to use supplied context, admit insufficient information, and return source filenames.

The local embedding is lightweight and test-friendly. A production semantic embedding provider can later replace only `app/rag/embeddings.py`.

## Install and configure

Python 3.11 or newer is required.

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally:

```text
GOOGLE_API_KEY=your_key_here
PUSHAN_LLM_MODEL=gemini-3.1-flash-lite
PUSHAN_API_URL=http://127.0.0.1:8000
PUSHAN_AUTOMATION_WEBHOOK_URL=
```

`.env` is ignored by Git. Never commit or paste real keys into source, tests, logs, screenshots, issues, or chat. Retrieval and tests work without a key; only live generation needs one. Pushan uses Gemini 3.1 Flash-Lite for high-volume, cost-efficient generation while keeping embeddings local so indexing and retrieval consume no Gemini quota. Google's free-tier terms currently state that submitted content may be used to improve its products; do not submit sensitive farm or personal data without reviewing the applicable terms.

Ordinary dashboard requests use a five-second timeout. Gemini-backed knowledge and agent requests use a separate 60-second timeout, while provider calls have bounded retries and return a controlled service error when Google is unreachable.

## Build the knowledge index

Run after installation and whenever a knowledge document changes:

```powershell
python -m app.rag.vector_store
```

This loads `knowledge/*.md`, chunks and embeds them locally, and persists Chroma under `artifacts/vector_store/`. Questions never silently rebuild the index.

## Train and run

Train the advisory model once:

```powershell
python -m app.ml.train
```

Then use two terminals:

```powershell
# Terminal 1
python -m uvicorn app.main_api:app --reload

# Terminal 2
python -m streamlit run frontend/streamlit_app.py
```

Open `http://localhost:8501`. API health is at `http://127.0.0.1:8000/health` and Swagger is at `/docs`. V0.9 adds `GET /approvals`, approval/rejection endpoints, `GET /workflows/{workflow_id}`, `GET /incidents`, and `GET /audit` alongside the knowledge and agent routes.

## Project structure

```text
Project_Pushan/
├── app/
│   ├── api/  database/  ml/  services/
│   ├── agents/
│   │   ├── state.py  tools.py  nodes.py
│   │   └── graph.py  agent_service.py
│   └── rag/
│       ├── loader.py  chunking.py  embeddings.py
│       └── vector_store.py  retriever.py  qa_service.py
│   └── workflows/
│       ├── guardrails.py  workflow_engine.py  approval_service.py
│       └── incident_service.py  notification_service.py  repository.py
├── knowledge/
│   ├── irrigation_basics.md  tomato_irrigation.md
│   ├── rice_irrigation.md  cotton_irrigation.md
│   └── drip_irrigation_sop.md
├── artifacts/vector_store/       # generated, ignored
├── frontend/  tests/
├── .env.example  README.md  requirements.txt
```

Every knowledge document is labeled as a prototype and ends with authoritative sources. It is educational and requires local agronomic validation.

## Tests

```powershell
python -m unittest discover -s tests
```

The suite uses local embeddings and mocked provider calls, so it makes no live paid model call. It verifies loading, retrieval, graph routes, finite retries, degraded operation, guardrails, durable approval and rejection, restart persistence, idempotency, notifications, incidents, auditing, API/UI integration, and earlier-version behaviour.

## V0.9 boundary

V0.9 remains local and prototype-grade. Execution, notifications, incidents, and approvals are simulations persisted in SQLite. The optional webhook is an integration seam for tools such as Power Automate, not a deployed automation. Pushan has no authentication, role-based access control, Docker, cloud deployment, MQTT, or real pump control. Production use would require identity, authorization, concurrency controls, calibrated agronomy, equipment interlocks, monitoring, and security review. This release does not begin V1.0.
