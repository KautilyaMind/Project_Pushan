"""Deterministic simulated sensor data for Pushan V0.2."""

from app.models import FarmInput, SensorReading


SIMULATED_SENSOR_DATA: dict[str, SensorReading] = {
    "FIELD_001": SensorReading(
        field_id="FIELD_001",
        soil_moisture=18,
        temperature=36,
        humidity=32,
        rain_probability=10,
        pump_status="OFFLINE",
        water_available_litres=10000,
        sensor_status="HEALTHY",
    ),
    "FIELD_002": SensorReading(
        field_id="FIELD_002",
        soil_moisture=35,
        temperature=29,
        humidity=55,
        rain_probability=20,
        pump_status="ONLINE",
        water_available_litres=8000,
        sensor_status="HEALTHY",
    ),
    "FIELD_003": SensorReading(
        field_id="FIELD_003",
        soil_moisture=20,
        temperature=30,
        humidity=50,
        rain_probability=15,
        pump_status="ONLINE",
        water_available_litres=1000,
        sensor_status="HEALTHY",
    ),
}

# Field metadata lives here beside the simulated fields so it has one source.
FIELD_CONFIGURATIONS: dict[str, dict[str, str | float]] = {
    "FIELD_001": {
        "crop": "tomato",
        "crop_stage": "flowering",
        "field_area_m2": 1000,
    },
    "FIELD_002": {
        "crop": "tomato",
        "crop_stage": "fruiting",
        "field_area_m2": 800,
    },
    "FIELD_003": {
        "crop": "tomato",
        "crop_stage": "flowering",
        "field_area_m2": 1000,
    },
}


def get_latest_reading(field_id: str) -> SensorReading:
    """Return the latest simulated reading for a supported field ID."""
    if not isinstance(field_id, str) or not field_id.strip():
        raise ValueError("field_id must be a non-empty string")

    normalized_field_id = field_id.strip().upper()
    try:
        return SIMULATED_SENSOR_DATA[normalized_field_id]
    except KeyError as error:
        raise ValueError(f"Unknown field ID: {field_id}") from error


def build_farm_input(
    reading: SensorReading,
    crop: str,
    crop_stage: str,
    field_area_m2: float,
) -> FarmInput:
    """Convert a sensor reading and field details into irrigation-engine input."""
    return FarmInput(
        soil_moisture=reading.soil_moisture,
        temperature=reading.temperature,
        humidity=reading.humidity,
        rain_probability=reading.rain_probability,
        crop=crop,
        crop_stage=crop_stage,
        field_area_m2=field_area_m2,
    )
