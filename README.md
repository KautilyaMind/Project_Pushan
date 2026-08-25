# Pushan — The Next-Gen AI Agriculture Engine (V0.3)

Pushan is a beginner-readable smart agriculture process-intelligence project.
V0.3 adds durable SQLite storage for fields, sensor readings, irrigation
recommendations, and final operational actions.

Despite its name, V0.3 still contains no machine learning or generative AI. Its
decisions remain deterministic and rule-based, and its crop thresholds remain
simplified prototype values rather than authoritative agronomic guidance.

## Project evolution

```text
V0.1
manual inputs → rule-based irrigation decision

V0.2
simulated sensors → irrigation decision → operational feasibility

V0.3
simulated sensors → persistent storage → irrigation decision history
                  → operational action history
```

## What V0.3 adds

- Automatic creation of `data/pushan.db` and its parent directory.
- Persistent field metadata and timestamped sensor readings.
- Irrigation recommendation and operational action history.
- Newest-first history retrieval by field ID.
- Configurable database paths so tests use temporary databases.
- Parameterized SQL, foreign-key checks, and clean connection handling.

History allows operators to audit previous decisions, compare readings over
time, understand system behavior, and eventually prepare trustworthy datasets
for analytics or machine learning.

> V0.3 introduces memory at the application level, not AI memory.

The application is simply storing structured historical records in SQLite.

## Architecture and workflow

```text
sensor_service.py       obtains deterministic sensor data
        ↓
repository.py           stores the sensor reading
        ↓
irrigation_engine.py    decides whether irrigation is needed
        ↓
repository.py           stores the recommendation
        ↓
operational_engine.py   checks whether execution is possible
        ↓
repository.py           stores the final action
```

`app/database/db.py` owns the database path, connections, foreign-key setting,
and schema creation. `app/database/repository.py` owns the small parameterized
queries used to save and retrieve records. Keeping them separate prevents SQL
from leaking into the engines or CLI and keeps schema setup distinct from
application data operations.

## Database schema

- `fields`: one metadata record per field, including crop, stage, and area.
- `sensor_readings`: timestamped environmental and equipment readings.
- `irrigation_decisions`: timestamped outputs from the irrigation engine.
- `operational_actions`: timestamped final actions after feasibility checks.

Each history table links to `fields.field_id`. Boolean values are stored as
SQLite integers (`0` or `1`), and timestamps use timezone-aware ISO 8601 text.

## Project structure

```text
Project_Pushan/
├── app/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   └── repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── sensor_service.py
│   ├── __init__.py
│   ├── irrigation_engine.py
│   ├── models.py
│   └── operational_engine.py
├── data/
│   └── pushan.db              created when the demo runs
├── tests/
│   ├── test_database.py
│   ├── test_irrigation_engine.py
│   ├── test_operational_engine.py
│   └── test_sensor_service.py
├── main.py
├── README.md
└── requirements.txt
```

## Requirements and usage

Python 3.11 or newer. V0.3 uses only the Python standard library.

```powershell
python main.py
python -m unittest discover -s tests
```

Running the demo processes `FIELD_001`, saves all three record types, and shows
up to three recent entries from each history. Repeated runs demonstrate that
the records persist in `data/pushan.db`.

## Limitations and possible V0.4 direction

V0.3 uses fixed sensor simulations and has no real device integration, web API,
dashboard, analytics, or AI. A logical V0.4 could add a small service layer for
field registration and historical summaries, plus controlled schema migrations
and retention rules. Those features are intentionally outside V0.3.
