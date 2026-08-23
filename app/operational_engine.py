"""Operational feasibility rules for Pushan V0.2."""

from .models import IrrigationRecommendation, OperationalDecision, SensorReading


def evaluate_operational_feasibility(
    recommendation: IrrigationRecommendation,
    sensor_reading: SensorReading,
) -> OperationalDecision:
    """Decide whether an irrigation recommendation can be executed safely."""
    common_values = {
        "irrigation_required": recommendation.irrigation_required,
        "recommended_water_litres": recommendation.recommended_water_litres,
        "risk_level": recommendation.risk_level,
    }

    if not recommendation.irrigation_required:
        return OperationalDecision(
            **common_values,
            execution_possible=False,
            action_required="NO_ACTION",
            reason=f"No irrigation action is required. {recommendation.reason}",
        )

    if sensor_reading.sensor_status == "FAULTY":
        return OperationalDecision(
            **common_values,
            execution_possible=False,
            action_required="CHECK_SENSOR",
            reason=(
                "Irrigation is required, but the sensor is faulty. Check the sensor "
                "before acting on potentially unreliable data."
            ),
        )

    if sensor_reading.pump_status == "OFFLINE":
        return OperationalDecision(
            **common_values,
            execution_possible=False,
            action_required="MAINTENANCE_REQUIRED",
            reason="The field requires irrigation, but the pump is offline.",
        )

    if sensor_reading.water_available_litres < recommendation.recommended_water_litres:
        water_deficit = (
            recommendation.recommended_water_litres
            - sensor_reading.water_available_litres
        )
        return OperationalDecision(
            **common_values,
            execution_possible=False,
            action_required="REFILL_WATER",
            reason=(
                f"Irrigation requires {recommendation.recommended_water_litres:g} L, "
                f"but only {sensor_reading.water_available_litres:g} L is available. "
                f"Refill the {water_deficit:g} L water deficit."
            ),
        )

    return OperationalDecision(
        **common_values,
        execution_possible=True,
        action_required="IRRIGATE",
        reason=(
            "The sensor is healthy, the pump is online, and sufficient water is "
            "available. Irrigation can safely proceed."
        ),
    )
