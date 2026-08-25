"""Load the trained V0.4 pipeline and produce advisory water predictions."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.models import FarmInput

from .train import DEFAULT_MODEL_PATH, FEATURES


@lru_cache(maxsize=4)
def load_model(model_path: str) -> Any:
    """Load and cache a complete preprocessing and regression pipeline."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"ML model not found at {path}. Run 'python -m app.ml.train' first."
        )
    return joblib.load(path)


def predict_water_requirement(
    farm_input: FarmInput,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> float:
    """Predict non-negative irrigation litres for one validated farm input."""
    input_data = pd.DataFrame(
        [
            {
                "soil_moisture": farm_input.soil_moisture,
                "temperature": farm_input.temperature,
                "humidity": farm_input.humidity,
                "rain_probability": farm_input.rain_probability,
                "field_area_m2": farm_input.field_area_m2,
                "crop": farm_input.crop.strip().lower(),
                "crop_stage": farm_input.crop_stage.strip().lower(),
            }
        ],
        columns=FEATURES,
    )
    model = load_model(str(Path(model_path).resolve()))
    predicted_litres = float(model.predict(input_data)[0])
    return round(max(0, predicted_litres), 2)
