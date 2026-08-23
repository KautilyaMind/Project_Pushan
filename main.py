"""Command-line demonstration of the Pushan V0.1 irrigation engine."""

from app.irrigation_engine import calculate_irrigation
from app.models import FarmInput


def main() -> None:
    """Run the example farm scenario and print its recommendation."""
    example_farm = FarmInput(
        soil_moisture=21,
        temperature=37,
        humidity=30,
        rain_probability=20,
        crop="tomato",
        crop_stage="flowering",
        field_area_m2=1000,
    )
    recommendation = calculate_irrigation(example_farm)

    print("Pushan V0.1 - Smart Irrigation Recommendation")
    print("-" * 47)
    print(f"Irrigation required: {'Yes' if recommendation.irrigation_required else 'No'}")
    print(f"Recommended water: {recommendation.recommended_water_litres:g} litres")
    print(f"Risk: {recommendation.risk_level}")
    print(f"Reason: {recommendation.reason}")


if __name__ == "__main__":
    main()
