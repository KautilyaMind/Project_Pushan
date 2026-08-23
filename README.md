# Pushan — A New-Gen Smart Irrigation Project (V0.2)

Pushan is a beginner-readable smart agriculture process-intelligence project.
V0.2 combines a deterministic sensor simulation with the existing rule-based
irrigation engine and a new operational feasibility check.

V0.2 remains intentionally rule-based. It does **not** use AI, machine learning,
external APIs, databases, or real IoT devices. Crop thresholds are simplified
prototype values and are not authoritative agronomic guidance.

## What changed from V0.1

```text
V0.1: Manual farm inputs → irrigation rules → recommendation

V0.2: Field ID → simulated sensor service → irrigation engine
      → operational feasibility → final action
```

The original irrigation rules and V0.1 tests remain in place.

## Irrigation requirement versus execution feasibility

The irrigation engine asks: **Does this field need water, and how much?** The
operational engine then asks: **Can that recommendation be executed safely now?**

A field may require irrigation from an agronomic perspective, but the action
may still be blocked because the pump is offline, the sensor is faulty, or
insufficient water is available.

Operational checks use this priority: irrigation requirement, sensor
reliability, pump availability, water availability, and finally permission to
irrigate.

## Architecture

- `app/models.py` defines validated farm, sensor, recommendation, and decision data.
- `app/services/sensor_service.py` returns deterministic readings for three fields
  and converts readings into the existing `FarmInput` model.
- `app/irrigation_engine.py` preserves the V0.1 agronomic calculation.
- `app/operational_engine.py` decides whether the recommendation can be executed.
- `main.py` demonstrates the complete FIELD_001 pipeline.

This separation allows a future sensor source to replace the simulation without
rewriting either decision engine.

## Project structure

```text
pushan/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   └── sensor_service.py
│   ├── __init__.py
│   ├── irrigation_engine.py
│   ├── models.py
│   └── operational_engine.py
├── tests/
│   ├── __init__.py
│   ├── test_irrigation_engine.py
│   ├── test_operational_engine.py
│   └── test_sensor_service.py
├── main.py
├── README.md
└── requirements.txt
```

## Requirements and usage

Python 3.11 or newer. No third-party packages are required.

```powershell
python main.py
python -m unittest discover -s tests
```

## FIELD_001 demonstration

FIELD_001 has dry soil, a healthy sensor, sufficient stored water, and an
offline pump. For a 1,000 m² tomato field, the engine recommends 6,325 L after
high-temperature and low-humidity adjustments. The operational engine blocks
execution and returns `MAINTENANCE_REQUIRED` because the pump is offline.

## Simulated fields

- `FIELD_001`: dry soil, healthy sensor, offline pump.
- `FIELD_002`: sufficient tomato soil moisture, healthy sensor, online pump.
- `FIELD_003`: dry soil, healthy sensor, online pump, insufficient stored water
  for a 1,000 m² tomato field.

## Limitations and possible V0.3 direction

V0.2 has fixed simulated values, no reading history, no persistence, and no
real device communication. A logical V0.3 could add timestamped readings,
configurable field profiles, and historical storage while retaining the same
engine boundaries. AI/ML should be considered only when sufficient trustworthy
data and a clearly defined prediction problem exist.
