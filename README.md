# Pushan — The Next-Gen AI Agriculture Engine

Pushan is a portfolio-grade AI process-intelligence platform for simulated irrigation operations. It combines deterministic rules, an advisory ML model, grounded RAG knowledge, controlled LangGraph orchestration, operational guardrails, persistent human approval, and auditable workflow automation. V1.0 packages the system as configurable FastAPI and Streamlit services with Docker, readiness checks, structured logs, integration tests, and CI. It is an engineering prototype—not production-certified agronomic or industrial control software.

## Problem

Agricultural decisions are often split across sensor readings, local operating knowledge, equipment status, human judgment, and disconnected records. A recommendation alone is insufficient: an operational system must explain the decision, check feasibility, enforce policy, obtain authorization when risk is high, avoid duplicate actions, and preserve an audit trail.

## Solution

Pushan connects simulated sensors to rule-based irrigation decisions and an advisory scikit-learn prediction. RAG retrieves relevant procedures from a local Chroma index, while LangGraph coordinates capabilities without allowing an LLM to override deterministic safety controls. Guardrails separate recommendation from execution; high-risk actions pause for human approval, while maintenance conditions create incidents and simulated notifications. SQLite preserves assessments, approvals, workflows, incidents, notifications, and audit history across restarts.

## Architecture

```text
Human Operator → Streamlit → FastAPI → LangGraph Agent
                                      ├─ Sensors
                                      ├─ Rules + ML advisory
                                      └─ RAG knowledge
                                             ↓
                                   Operational Engine
                                             ↓
                                        Guardrails
                                             ↓
                                  Approval required?
                                   ├─ No  → Workflow
                                   └─ Yes → Human Review
                                                ├─ Approve → Workflow
                                                └─ Reject  → Stop
                                             ↓
                              Incidents + Notifications + Audit
                                             ↓
                                           SQLite

Supporting layers: configuration · structured logging · request IDs
                   readiness · tests · Docker · GitHub Actions
```

See [docs/architecture.md](docs/architecture.md) for component and data-flow details.

## Version evolution

| Version | Capability |
|---|---|
| V0.1 | Rule-based irrigation engine |
| V0.2 | Sensor simulation and operational feasibility |
| V0.3 | SQLite persistence and history |
| V0.4 | Machine-learning advisory prediction |
| V0.5 | FastAPI backend |
| V0.6 | Streamlit dashboard |
| V0.7 | RAG agriculture knowledge system |
| V0.8 | LangGraph controlled orchestration |
| V0.9 | Human approval, guardrails, and workflow automation |
| V1.0 | Deployable, configurable, observable portfolio release |

## Technology stack

- Python 3.12, FastAPI, Uvicorn, Pydantic
- Streamlit and HTTPX
- SQLite
- pandas, scikit-learn, and joblib
- LangChain, LangGraph, Chroma
- deterministic local hash embeddings (`local-hash-v1`)
- Google Gemini (`gemini-3.1-flash-lite` by default) for grounded generation
- Docker Compose and GitHub Actions

## Local installation

```powershell
cd "C:\Users\sriad\OneDrive\Documents\ChatGPT\pushan\code\pushan v0.1"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` is local and ignored by Git. Add `GOOGLE_API_KEY` only if live Gemini generation is required. Never commit keys, webhook URLs containing credentials, passwords, or tokens.

Configuration is centralized in `app/config.py`. It covers environment, API, database/model/vector paths, Gemini and embedding models, guardrail threshold, webhook URL/timeout, and log level.

## Prepare local artifacts

Initialize or upgrade SQLite without deleting existing data:

```powershell
python -m app.database.init_db
```

Train the advisory model and write model metadata:

```powershell
python -m app.ml.train
```

Index Markdown and PDF knowledge files and write index metadata:

```powershell
python -m app.rag.index
```

The ML training data is synthetic/domain-generated development data. Neither the model nor the prototype thresholds are production validated.

## Run Pushan

Backend only:

```powershell
python -m uvicorn app.main_api:app --host 127.0.0.1 --port 8000
```

Backend and frontend locally: keep the backend command running, then use a second activated terminal:

```powershell
$env:PUSHAN_API_URL = "http://127.0.0.1:8000"
python -m streamlit run frontend/streamlit_app.py --server.port 8501
```

Open `http://127.0.0.1:8501`. API documentation is at `http://127.0.0.1:8000/docs`.

Docker startup:

```powershell
docker compose up --build
```

Compose exposes API port 8000 and UI port 8501. Bind mounts preserve `data/` and `artifacts/` across container replacement. Docker must be installed separately.

## Health, readiness, and observability

`GET /health` answers only “is the API process alive?”

```json
{"status":"ok","service":"Pushan","version":"1.0.0"}
```

`GET /ready` checks SQLite, model compatibility, knowledge-index availability, and webhook configuration:

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "ml_model": "ok",
    "knowledge_base": "ok",
    "automation_webhook": "not_configured"
  }
}
```

A missing optional model or index produces `degraded`; an unconfigured webhook is informational. Requests accept or generate `X-Request-ID`, return it with `X-Process-Time-Ms`, and write JSON logs. Unexpected failures return a safe error envelope without stack traces, paths, or secrets.

## Testing

```powershell
python -m unittest discover -s tests
python -m unittest discover -s tests/integration
```

With the API running:

```powershell
python scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

Tests mock external providers and require no paid calls. GitHub Actions runs the complete suite on pushes and pull requests.

## Key API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /ready` | Dependency readiness |
| `GET /fields` | Configured fields |
| `GET /fields/{id}/sensor` | Current simulated reading |
| `POST /irrigation/recommend` | Rules, ML, operations, persistence |
| `POST /knowledge/ask` | Grounded RAG answer |
| `POST /agent/run` | Controlled LangGraph workflow |
| `GET /approvals` | Pending approvals |
| `POST /approvals/{id}/approve` | Authorize and resume |
| `POST /approvals/{id}/reject` | Reject and block |
| `GET /workflows/{id}` | Workflow state |
| `GET /incidents` | Operational incidents |
| `GET /audit` | Audit trail |

## Safety and control hierarchy

```text
LLM / LangGraph → understands, retrieves, routes, and explains
ML              → predicts advisory demand
Rules           → make deterministic irrigation decisions
Operations      → check equipment and resource feasibility
Guardrails      → enforce deterministic action policy
Human           → authorizes selected high-risk actions
Workflow engine → performs idempotent simulated downstream tasks
```

No higher layer bypasses a lower control. “Technically executable” and “authorized to execute” are separate API concepts. Approval and workflow state are persisted so a restart cannot silently lose a pending decision.

## Limitations

- Simulated sensors and workflow execution; no real pump or industrial hardware
- Prototype agronomic thresholds requiring local expert validation
- Synthetic/domain-generated ML development data
- No production authentication, authorization, or tenancy
- Local SQLite is not intended for high concurrency
- RAG quality depends on supplied documents; live generation requires Gemini connectivity
- Generic webhook seam, not a complete Power Automate deployment
- No Kubernetes, production monitoring stack, or production certification

Potential V1.x work includes authentication, PostgreSQL, calibrated field trials, background jobs, signed webhooks, richer metrics, and real device adapters—but none is implemented in V1.0.

## Demonstration

Use [docs/demo_guide.md](docs/demo_guide.md) for a deterministic 5–8 minute walkthrough.
