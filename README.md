# Pushan — A New-Gen Smart Irrigation Project (V0.1)

Pushan V0.1 is a beginner-readable, rule-based irrigation decision engine. It
uses farm measurements and simple crop requirements to decide whether a field
needs irrigation and, when it does, recommend an amount of water.

V0.1 is intentionally rule-based and does **not** yet use AI or machine
learning. Its crop values are simplified prototype values and are not
scientifically authoritative agronomic guidance.

## What V0.1 does

- Supports tomato, rice, and cotton.
- Validates farm input before making a recommendation.
- Avoids watering soil that already has sufficient moisture.
- Postpones irrigation when the probability of rain is at least 70%.
- Calculates water from field area and the selected crop's rate.
- Adds 15% in temperatures above 35°C and then 10% in humidity below 35%.
- Reports LOW, MEDIUM, HIGH, or UNKNOWN risk.

## Architecture

The data classes in `app/models.py` define and validate the engine's inputs and
outputs. `app/irrigation_engine.py` contains all business rules. `main.py` is
only a command-line demonstration. This separation lets future APIs, agents,
and workflow tools reuse the same engine without depending on a user interface.

## Project structure

```text
pushan v0.1/
├── app/
│   ├── __init__.py
│   ├── models.py
│   └── irrigation_engine.py
├── tests/
│   ├── __init__.py
│   └── test_irrigation_engine.py
├── main.py
├── requirements.txt
└── README.md
```

## Requirements

Python 3.11 or newer. No third-party packages are required.

## Run the program

From the `pushan v0.1` directory:

```powershell
python main.py
```

## Run the tests

```powershell
python -m unittest discover -s tests -v
```

## Sample output

```text
Pushan V0.1 - Smart Irrigation Recommendation
-----------------------------------------------
Irrigation required: Yes
Recommended water: 6325 litres
Risk: MEDIUM
Reason: Soil moisture is 21%, below the target threshold of 30%. Water was adjusted by 15% for high temperature and 10% for low humidity.
```

## Limitations of V0.1

- Crop thresholds are simplified constants, not region-specific agronomy.
- Decisions use current values only; no sensor history or weather service exists.
- Crop stage is recorded but does not yet change the calculation.
- There is no database, API, graphical interface, authentication, or deployment.
- There is no AI/ML, prediction, optimization, or automatic device control.

## Planned future versions

Future versions may add richer crop- and growth-stage rules, configuration,
historical sensor data, weather integration, an API, persistence, explainable
ML predictions, workflow automation, monitoring, and deployment. Each addition
should continue to reuse or evolve the isolated business-logic layer.
