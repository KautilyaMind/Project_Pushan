"""Command-line demonstration of the persistent Pushan V0.3 workflow."""

from typing import Any

from app.database.db import initialize_database
from app.database.repository import (
    get_action_history,
    get_decision_history,
    get_sensor_history,
    save_field,
    save_irrigation_decision,
    save_operational_decision,
    save_sensor_reading,
)
from app.irrigation_engine import calculate_irrigation
from app.operational_engine import evaluate_operational_feasibility
from app.services.sensor_service import (
    FIELD_CONFIGURATIONS,
    build_farm_input,
    get_latest_reading,
)


def yes_or_no(value: bool) -> str:
    """Return a readable label for a Boolean value."""
    return "YES" if value else "NO"


def print_history(title: str, records: list[dict[str, Any]], detail: str) -> None:
    """Print a compact newest-first history section."""
    print(f"\n{title}:")
    for record in records:
        print(f"- {record['timestamp']} | {detail.format(**record)}")


def main() -> None:
    """Run FIELD_001 through decision engines and persistent storage."""
    field_id = "FIELD_001"
    field_config = FIELD_CONFIGURATIONS[field_id]

    initialize_database()
    save_field(
        field_id=field_id,
        crop=str(field_config["crop"]),
        crop_stage=str(field_config["crop_stage"]),
        field_area_m2=float(field_config["field_area_m2"]),
    )

    sensor_reading = get_latest_reading(field_id)
    save_sensor_reading(sensor_reading)

    farm_input = build_farm_input(
        reading=sensor_reading,
        crop=str(field_config["crop"]),
        crop_stage=str(field_config["crop_stage"]),
        field_area_m2=float(field_config["field_area_m2"]),
    )
    recommendation = calculate_irrigation(farm_input)
    save_irrigation_decision(field_id, recommendation)

    decision = evaluate_operational_feasibility(recommendation, sensor_reading)
    save_operational_decision(field_id, decision)

    print("PUSHAN V0.3 - The Next-Gen AI Agriculture Engine")
    print("-" * 51)
    print(f"Field: {field_id}")
    print("\nCurrent Sensor Reading:")
    print(f"Soil moisture: {sensor_reading.soil_moisture:g}%")
    print(f"Temperature: {sensor_reading.temperature:g} degrees C")
    print(f"Humidity: {sensor_reading.humidity:g}%")
    print(f"Rain probability: {sensor_reading.rain_probability:g}%")
    print(f"Pump: {sensor_reading.pump_status}")
    print(f"Sensor: {sensor_reading.sensor_status}")
    print(f"Water available: {sensor_reading.water_available_litres:g} L")

    print("\nIrrigation Recommendation:")
    print(f"Required: {yes_or_no(recommendation.irrigation_required)}")
    print(f"Recommended water: {recommendation.recommended_water_litres:g} L")
    print(f"Risk: {recommendation.risk_level}")

    print("\nOperational Decision:")
    print(f"Execution possible: {yes_or_no(decision.execution_possible)}")
    print(f"Action: {decision.action_required}")
    print(f"Reason: {decision.reason}")
    print("\nSaved to database successfully.")

    print_history(
        "Recent sensor history",
        get_sensor_history(field_id, limit=3),
        "moisture {soil_moisture:g}% | pump {pump_status}",
    )
    print_history(
        "Recent decision history",
        get_decision_history(field_id, limit=3),
        "required {irrigation_required} | water {recommended_water_litres:g} L",
    )
    print_history(
        "Recent action history",
        get_action_history(field_id, limit=3),
        "action {action_required} | executable {execution_possible}",
    )


if __name__ == "__main__":
    main()
