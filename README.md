# Pushan — The Next-Gen AI Agriculture Engine (V0.5)

Pushan is a prototype irrigation process-intelligence platform. V0.5 exposes
its existing rule, machine-learning, operational, and persistence capabilities
through a validated FastAPI service while preserving the command-line demo.

V0.5 turns Pushan's internal Python capabilities into reusable HTTP services
that can be consumed by future dashboards, mobile applications, automation
systems, AI agents, or other enterprise software.

## Project evolution

```text
V0.1  Rule-Based Irrigation Engine
V0.2  Sensor Simulation + Operational Feasibility
V0.3  SQLite Persistence + Historical Records
V0.4  Machine-Learning Irrigation Prediction
V0.5  FastAPI Service Layer
```

## Architecture

```text
Client / Browser / Future UI
              ↓
       FastAPI routes + schemas
              ↓
       Assessment service
              ↓
 ┌────────────┼─────────────┐
 ↓            ↓             ↓
Rules     ML advisory    SQLite history
 ↓
Operational feasibility
```

The irrigation engine contains business logic. FastAPI only exposes that logic
to external consumers. Routes validate HTTP input, call reusable services, and
format responses; they do not reimplement irrigation calculations.

The ML model remains advisory and never controls pumps. The deterministic rule
recommendation and operational constraints remain authoritative.

## Installation

Python 3.11 or newer is required.

```powershell
python -m pip install -r requirements.txt
```

V0.5 directly depends on scikit-learn, pandas, joblib, FastAPI, Uvicorn,
Pydantic, and HTTPX.

## Train the model

The model must be trained before running ML-backed API requests:

```powershell
python -m app.ml.train
```

This creates 1,000 deterministic **synthetic** training examples and evaluates
Linear Regression and Random Forest. The better complete preprocessing/model
pipeline is saved locally to `artifacts/irrigation_model.joblib`.

The data is for demonstrating the ML pipeline, not validated real agricultural
data. Generated CSV, model, and SQLite files are ignored by Git.

## Run the interfaces

Command-line demonstration:

```powershell
python main.py
```

FastAPI service:

```powershell
python -m uvicorn app.main_api:app --reload
```

After startup:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service status and version |
| `GET` | `/fields` | Configured field metadata |
| `GET` | `/fields/{field_id}/sensor` | Current simulated reading |
| `POST` | `/irrigation/recommend` | Complete persisted assessment |
| `POST` | `/ml/predict` | Direct advisory ML prediction |
| `GET` | `/fields/{field_id}/history/sensors` | Recent sensor history |
| `GET` | `/fields/{field_id}/history/decisions` | Rule-decision history |
| `GET` | `/fields/{field_id}/history/actions` | Operational-action history |

History endpoints accept `?limit=10`, with values from 1 through 100.

## Sample requests

Health:

```powershell
curl http://127.0.0.1:8000/health
```

Complete FIELD_001 assessment:

```powershell
curl -X POST http://127.0.0.1:8000/irrigation/recommend `
  -H "Content-Type: application/json" `
  -d '{"field_id":"FIELD_001","crop":"tomato","crop_stage":"flowering","field_area_m2":1000}'
```

Direct ML prediction:

```powershell
curl -X POST http://127.0.0.1:8000/ml/predict `
  -H "Content-Type: application/json" `
  -d '{"soil_moisture":20,"temperature":34,"humidity":40,"rain_probability":15,"crop":"tomato","crop_stage":"flowering","field_area_m2":1000}'
```

Recent sensor history:

```powershell
curl "http://127.0.0.1:8000/fields/FIELD_001/history/sensors?limit=5"
```

## Example assessment response

```json
{
  "field_id": "FIELD_001",
  "sensor": {
    "field_id": "FIELD_001",
    "soil_moisture": 18,
    "temperature": 36,
    "humidity": 32,
    "rain_probability": 10,
    "pump_status": "OFFLINE",
    "water_available_litres": 10000,
    "sensor_status": "HEALTHY"
  },
  "rule_based": {
    "irrigation_required": true,
    "recommended_water_litres": 6325,
    "risk_level": "MEDIUM",
    "reason": "Soil moisture is below the target threshold."
  },
  "ml": {
    "predicted_water_litres": 3039.66,
    "model_version": "v0.4"
  },
  "comparison": {
    "absolute_difference_litres": 3285.34,
    "difference_percentage": 51.94
  },
  "operational": {
    "execution_possible": false,
    "action_required": "MAINTENANCE_REQUIRED",
    "reason": "The field requires irrigation, but the pump is offline."
  }
}
```

Exact ML values depend on the trained artifact.

## Validation and errors

Pydantic validates external percentages and positive field areas before they
reach domain code. The API uses consistent status codes:

- `200`: successful request
- `404`: unknown field
- `422`: invalid request body or query parameter
- `503`: trained ML model unavailable
- `500`: unexpected internal error with no stack trace exposed to the client

## Project structure

```text
Project_Pushan/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── database/
│   ├── ml/
│   ├── services/
│   │   ├── assessment_service.py
│   │   └── sensor_service.py
│   ├── irrigation_engine.py
│   ├── main_api.py
│   ├── models.py
│   └── operational_engine.py
├── tests/
│   └── test_api.py
├── main.py
├── README.md
└── requirements.txt
```

## Testing

```powershell
python -m unittest discover -s tests
```

API tests use a temporary SQLite database and a small temporary trained model.
They do not modify development history or require the production model artifact.

## Limitations and possible V0.6 direction

V0.5 uses deterministic simulated sensors, synthetic ML training data, and local
SQLite persistence. It has no authentication, real IoT connection, production
deployment, or user interface. A logical V0.6 could add API authentication,
request correlation, prediction logging/model version records, and production
configuration management. No V0.6 features are included.
