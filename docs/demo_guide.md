# Pushan V1.0 Interview Demo Guide

Target duration: 5–8 minutes. Prepare the model and index first, then start API and UI using the README commands.

## 0:00–1:00 — Overview and status

Open `http://127.0.0.1:8501`. Show V1.0 and System Status. Explain that health means the API is alive while readiness checks SQLite, ML, and RAG artifacts.

## 1:00–2:30 — FIELD_001 operational block

Select `FIELD_001` and run the assessment. It needs water, but the pump is offline. Explain: rules determine need, ML gives an advisory comparison, and operations block irrigation. Ask the agent `Assess FIELD_001`, then show the maintenance incident, notification, and audit trail. No real pump is controlled.

## 2:30–4:00 — Human approval

Use a prepared high-risk/high-volume pending request. In Approval Center show field, volume, risk, reason, and request ID. Approve it with a note, then show `COMPLETED` and audit events. Explain that the database-backed pause survives API restarts.

## 4:00–5:00 — Grounded knowledge

Ask `What should I check when drip irrigation pressure is low?` Show the grounded answer and `drip_irrigation_sop.md`. If Gemini is unavailable, explain that retrieval is local, generation is external, and automated tests mock the provider.

## 5:00–6:30 — Controlled agent

Ask `Analyse FIELD_001 and explain whether irrigation should run.` Show the LangGraph trace. Emphasize that LLM/RAG guidance cannot override operations or guardrails.

## 6:30–7:30 — Engineering finish

Briefly show `/health`, `/ready`, Swagger, structured request logs, Docker Compose, GitHub Actions, and automated tests. Close with limitations: simulated telemetry, prototype thresholds/data, no authentication, and no real equipment control.
