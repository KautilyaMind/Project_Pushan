"""Generate deterministic synthetic training data for the V0.4 prototype.

The generated rows are demonstrations of an ML workflow, not real farm data or
validated agronomic guidance.
"""

from pathlib import Path
import random

import pandas as pd

from app.irrigation_engine import CROP_REQUIREMENTS


CROP_STAGES = ("seedling", "vegetative", "flowering", "maturity")
STAGE_FACTORS = {
    "seedling": 0.75,
    "vegetative": 1.00,
    "flowering": 1.15,
    "maturity": 0.85,
}
TRAINING_DATA_PATH = Path("data") / "training_data.csv"
REQUIRED_COLUMNS = [
    "soil_moisture",
    "temperature",
    "humidity",
    "rain_probability",
    "field_area_m2",
    "crop",
    "crop_stage",
    "recommended_water_litres",
]


def generate_training_data(
    num_samples: int = 1000,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Return reproducible synthetic examples of irrigation water demand."""
    if num_samples <= 0:
        raise ValueError("num_samples must be greater than 0")

    random_generator = random.Random(random_seed)
    crops = tuple(CROP_REQUIREMENTS)
    records: list[dict[str, str | float]] = []

    for _ in range(num_samples):
        crop = random_generator.choice(crops)
        crop_stage = random_generator.choice(CROP_STAGES)
        soil_moisture = random_generator.uniform(5, 60)
        temperature = random_generator.uniform(15, 45)
        humidity = random_generator.uniform(20, 95)
        rain_probability = random_generator.uniform(0, 100)
        field_area_m2 = random_generator.uniform(100, 5000)

        target = _synthetic_water_target(
            soil_moisture=soil_moisture,
            temperature=temperature,
            humidity=humidity,
            rain_probability=rain_probability,
            crop=crop,
            crop_stage=crop_stage,
            field_area_m2=field_area_m2,
            random_generator=random_generator,
        )
        records.append(
            {
                "soil_moisture": round(soil_moisture, 2),
                "temperature": round(temperature, 2),
                "humidity": round(humidity, 2),
                "rain_probability": round(rain_probability, 2),
                "field_area_m2": round(field_area_m2, 2),
                "crop": crop,
                "crop_stage": crop_stage,
                "recommended_water_litres": target,
            }
        )

    return pd.DataFrame(records, columns=REQUIRED_COLUMNS)


def save_training_data(
    data: pd.DataFrame,
    output_path: str | Path = TRAINING_DATA_PATH,
) -> Path:
    """Save generated prototype data to CSV and return the created path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False)
    return path


def _synthetic_water_target(
    *,
    soil_moisture: float,
    temperature: float,
    humidity: float,
    rain_probability: float,
    crop: str,
    crop_stage: str,
    field_area_m2: float,
    random_generator: random.Random,
) -> float:
    """Calculate a transparent but richer target than the V0.1 rule set."""
    crop_requirement = CROP_REQUIREMENTS[crop]
    minimum_moisture = crop_requirement["minimum_soil_moisture"]
    crop_rate = crop_requirement["water_litres_per_m2"]

    moisture_deficit_factor = max(
        0.0,
        (minimum_moisture + 10 - soil_moisture) / (minimum_moisture + 10),
    )
    temperature_factor = 1 + max(temperature - 30, 0) * 0.015
    low_humidity_factor = 1 + max(45 - humidity, 0) * 0.008
    rain_factor = max(0.10, 1 - rain_probability / 110)
    stage_factor = STAGE_FACTORS[crop_stage]

    demand = (
        field_area_m2
        * crop_rate
        * moisture_deficit_factor
        * temperature_factor
        * low_humidity_factor
        * rain_factor
        * stage_factor
    )
    controlled_noise = random_generator.gauss(0, max(demand * 0.03, 5))
    return round(max(0, demand + controlled_noise), 2)
