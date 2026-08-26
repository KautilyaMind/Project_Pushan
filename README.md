# Pushan — The Next-Gen AI Agriculture Engine (V0.8)

Pushan is a prototype smart-irrigation process-intelligence platform. V0.8 adds controlled LangGraph orchestration while preserving the existing sensor, rule, ML, operational, SQLite, API, dashboard, and RAG layers.

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
```

V0.8 converts Pushan's previously independent capabilities into tools coordinated by a stateful LangGraph workflow. The agent determines which capabilities are needed, executes them in a controlled sequence, handles failures, and produces a unified response.

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

Open `http://localhost:8501`. API health is at `http://127.0.0.1:8000/health`, Swagger at `/docs`, the knowledge route is `POST /knowledge/ask`, and agent orchestration is `POST /agent/run`.

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

The suite uses local embeddings and mocked provider calls, so it makes no live paid model call. It verifies loading, retrieval, graph routes, node updates, finite retries, degraded operation, safety constraints, API/UI integration, and V0.1–V0.7 behaviour.

## V0.8 boundary

V0.8 remains local and prototype-grade. It introduces one controlled state graph, not a multi-agent system. It has no Power Automate, UiPath, approval interrupts, Docker, cloud deployment, authentication, MQTT, or real IoT control. Its explicit state and tool boundaries prepare Pushan for later automation integration without implementing V0.9.
