"""Rule-based irrigation decisions for Pushan V0.1."""

from .models import FarmInput, IrrigationRecommendation


# Simplified prototype values; these are not authoritative agronomic guidance.
CROP_REQUIREMENTS: dict[str, dict[str, float]] = {
    "tomato": {
        "minimum_soil_moisture": 30,
        "water_litres_per_m2": 5.0,
    },
    "rice": {
        "minimum_soil_moisture": 45,
        "water_litres_per_m2": 8.0,
    },
    "cotton": {
        "minimum_soil_moisture": 25,
        "water_litres_per_m2": 4.0,
    },
}


def calculate_irrigation(data: FarmInput) -> IrrigationRecommendation:
    """Calculate an irrigation recommendation from validated farm input."""
    crop_name = data.crop.strip().lower()
    crop_requirement = CROP_REQUIREMENTS.get(crop_name)

    if crop_requirement is None:
        return IrrigationRecommendation(
            irrigation_required=False,
            recommended_water_litres=0,
            risk_level="UNKNOWN",
            reason=f"Unsupported crop: {data.crop}. No recommendation is available.",
        )

    minimum_moisture = crop_requirement["minimum_soil_moisture"]

    if data.soil_moisture >= minimum_moisture:
        return IrrigationRecommendation(
            irrigation_required=False,
            recommended_water_litres=0,
            risk_level="LOW",
            reason=(
                f"Soil moisture is {data.soil_moisture:g}%, which meets or exceeds "
                f"the target threshold of {minimum_moisture:g}%."
            ),
        )

    if data.rain_probability >= 70:
        return IrrigationRecommendation(
            irrigation_required=False,
            recommended_water_litres=0,
            risk_level="LOW",
            reason=(
                f"Soil moisture is {data.soil_moisture:g}% (target: "
                f"{minimum_moisture:g}%), but irrigation is postponed because "
                f"rainfall is likely ({data.rain_probability:g}% probability)."
            ),
        )

    water_required = data.field_area_m2 * crop_requirement["water_litres_per_m2"]
    adjustments: list[str] = []

    if data.temperature > 35:
        water_required *= 1.15
        adjustments.append("15% for high temperature")

    if data.humidity < 35:
        water_required *= 1.10
        adjustments.append("10% for low humidity")

    moisture_deficit = minimum_moisture - data.soil_moisture
    if moisture_deficit > 15:
        risk_level = "HIGH"
    elif moisture_deficit > 8:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    adjustment_text = ""
    if adjustments:
        adjustment_text = f" Water was adjusted by {' and '.join(adjustments)}."

    return IrrigationRecommendation(
        irrigation_required=True,
        recommended_water_litres=round(water_required, 2),
        risk_level=risk_level,
        reason=(
            f"Soil moisture is {data.soil_moisture:g}%, below the target "
            f"threshold of {minimum_moisture:g}%.{adjustment_text}"
        ),
    )
