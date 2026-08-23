"""Command-line demonstration of the Pushan V0.2 decision flow."""

from app.irrigation_engine import calculate_irrigation
from app.operational_engine import evaluate_operational_feasibility
from app.services.sensor_service import build_farm_input, get_latest_reading


def yes_or_no(value: bool) -> str:
    """Return a readable label for a Boolean value."""
    return "YES" if value else "NO"


def main() -> None:
    """Run FIELD_001 through the complete V0.2 decision pipeline."""
    sensor_reading = get_latest_reading("FIELD_001")

    print("Pushan V0.2 - Smart Irrigation Operational Decision")
    print("-" * 53)
    print(f"Field: {sensor_reading.field_id}")
    print()
    print(f"Soil moisture: {sensor_reading.soil_moisture:g}%")
    print(f"Temperature: {sensor_reading.temperature:g} degrees C")
    print(f"Humidity: {sensor_reading.humidity:g}%")
    print(f"Rain probability: {sensor_reading.rain_probability:g}%")
    print(f"Pump status: {sensor_reading.pump_status}")
    print(f"Sensor status: {sensor_reading.sensor_status}")
    print(f"Water available: {sensor_reading.water_available_litres:g} L")

    farm_input = build_farm_input(
        reading=sensor_reading,
        crop="tomato",
        crop_stage="flowering",
        field_area_m2=1000,
    )
    recommendation = calculate_irrigation(farm_input)
    decision = evaluate_operational_feasibility(recommendation, sensor_reading)

    print()
    print(f"Irrigation required: {yes_or_no(recommendation.irrigation_required)}")
    print(f"Recommended water: {recommendation.recommended_water_litres:g} L")
    print(f"Risk: {recommendation.risk_level}")
    print()
    print(f"Execution possible: {yes_or_no(decision.execution_possible)}")
    print(f"Action required: {decision.action_required}")
    print()
    print("Reason:")
    print(decision.reason)


if __name__ == "__main__":
    main()
