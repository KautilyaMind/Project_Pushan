"""Train, evaluate, and persist Pushan V0.4 regression models."""

from math import sqrt
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .data_generator import generate_training_data, save_training_data


NUMERIC_FEATURES = [
    "soil_moisture",
    "temperature",
    "humidity",
    "rain_probability",
    "field_area_m2",
]
CATEGORICAL_FEATURES = ["crop", "crop_stage"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "recommended_water_litres"
DEFAULT_MODEL_PATH = Path("artifacts") / "irrigation_model.joblib"


def build_model_pipeline(model: Any) -> Pipeline:
    """Build reusable preprocessing followed by the supplied regressor."""
    preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", "passthrough", NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    return Pipeline([("preprocessing", preprocessing), ("model", model)])


def train_and_evaluate_models(
    data: pd.DataFrame,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    *,
    random_state: int = 42,
    n_estimators: int = 100,
) -> dict[str, Any]:
    """Train two regressors, save the better pipeline, and return metrics."""
    missing_columns = set(FEATURES + [TARGET]) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Training data is missing columns: {sorted(missing_columns)}")

    features = data[FEATURES]
    target = data[TARGET]
    # Splitting happens before pipeline fitting, preventing preprocessing leakage.
    train_features, test_features, train_target, test_target = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=random_state,
    )

    candidates = {
        "Linear Regression": build_model_pipeline(LinearRegression()),
        "Random Forest": build_model_pipeline(
            RandomForestRegressor(
                n_estimators=n_estimators,
                random_state=random_state,
                n_jobs=1,
            )
        ),
    }
    metrics: dict[str, dict[str, float]] = {}

    for model_name, pipeline in candidates.items():
        pipeline.fit(train_features, train_target)
        predictions = pipeline.predict(test_features)
        metrics[model_name] = {
            "mae": float(mean_absolute_error(test_target, predictions)),
            "rmse": float(sqrt(mean_squared_error(test_target, predictions))),
            "r2": float(r2_score(test_target, predictions)),
        }

    selected_model_name = min(
        metrics,
        key=lambda name: (metrics[name]["rmse"], metrics[name]["mae"]),
    )
    output_path = Path(model_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(candidates[selected_model_name], output_path)

    return {
        "metrics": metrics,
        "selected_model": selected_model_name,
        "model_path": output_path,
    }


def print_evaluation(results: dict[str, Any]) -> None:
    """Print readable model metrics and the selected production pipeline."""
    print("MODEL EVALUATION")
    print("-" * 30)
    for model_name, metrics in results["metrics"].items():
        print(f"\n{model_name}")
        print(f"MAE: {metrics['mae']:.2f} L")
        print(f"RMSE: {metrics['rmse']:.2f} L")
        print(f"R2: {metrics['r2']:.4f}")
    print(f"\nSelected model: {results['selected_model']}")
    print(f"Saved to: {results['model_path']}")


def main() -> None:
    """Generate 1,000 examples, evaluate models, and save the best pipeline."""
    training_data = generate_training_data(num_samples=1000, random_seed=42)
    data_path = save_training_data(training_data)
    results = train_and_evaluate_models(training_data)
    print(f"Synthetic training data saved to: {data_path}")
    print_evaluation(results)


if __name__ == "__main__":
    main()
