# Pushan V1.0 Architecture

## System flow

```text
Operator → Streamlit → FastAPI → LangGraph
                                  ├─ Sensor service
                                  ├─ Rule engine
                                  ├─ ML predictor
                                  └─ RAG retriever + Gemini
                                         ↓
                                Operational feasibility
                                         ↓
                                    Guardrails
                                         ↓
                         Auto-execute or persisted approval
                                         ↓
                     Workflow → incident → notification/webhook
                                         ↓
                            SQLite records + audit trail
```

## Components

- **Frontend:** presents overview, assessment, knowledge, agent trace, approvals, incidents, history, audit, and readiness. It uses HTTP and owns no business logic.
- **API:** validates contracts, maps errors, adds correlation IDs and timings, and exposes liveness/readiness.
- **Agent:** LangGraph conditionally coordinates field assessment, ML, RAG, and response assembly. It is controlled orchestration, not unrestricted autonomy.
- **Sensor service:** returns deterministic simulated telemetry.
- **Rule engine:** makes the authoritative prototype irrigation recommendation.
- **ML:** estimates demand as advisory evidence. Missing ML never bypasses rules.
- **RAG:** embeds local Markdown/PDF material into Chroma and sends retrieved context to Gemini for grounded generation with sources.
- **Operational engine:** checks equipment and resource feasibility.
- **Guardrails:** enforce deterministic policy after reasoning and before action.
- **Approval service:** persists human decisions so they survive restarts.
- **Workflow engine:** executes idempotent simulated actions and prevents duplicates.
- **Incident/notification services:** record faults and optionally POST a bounded generic webhook.
- **Database:** stores history, approvals, workflows, incidents, notifications, audit events, and schema version.

## Reliability boundaries

Health is liveness; readiness checks feature dependencies. External failures are bounded and reported without crashing deterministic processing. Stable idempotency prevents repeated execution. JSON logs include component and request ID without secrets. Database initialization is additive and never resets data automatically.

## Final SQLite schema

`fields`, `sensor_readings`, `irrigation_decisions`, `operational_actions`, `approval_requests`, `workflow_executions`, `incidents`, `notifications`, `audit_log`, and `schema_version`.

## Agriculture-to-process-intelligence mapping

This mapping illustrates architecture transfer only; V1.0 contains no manufacturing integration.

| Pushan agriculture | Generic process intelligence |
|---|---|
| Field | Manufacturing tool or process |
| Sensor reading | Equipment/process telemetry |
| Soil-moisture anomaly | Process-parameter anomaly |
| Irrigation recommendation | Process-adjustment recommendation |
| Pump status | Equipment availability/status |
| Agriculture SOP | Manufacturing SOP |
| Farm operator | Process engineer |
| Irrigation incident | Quality or maintenance incident |
| Water prediction | Process or yield prediction |

The reusable pattern is telemetry → deterministic decision → advisory prediction/knowledge → operational policy → approval → idempotent workflow → audit.

## Deployment topology

Docker Compose builds independent API and UI images. The browser reaches Streamlit on `localhost:8501`; Streamlit calls `http://pushan-api:8000` on the Compose network. Host mounts preserve SQLite, model metadata/artifact, and the Chroma index. This remains portfolio-grade with no production identity, orchestration, or high-availability layer.
