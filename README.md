# Pushan — The Next-Gen AI Agriculture Engine (V0.4)

Pushan is a smart agriculture process-intelligence prototype. V0.4 introduces
a supervised machine-learning regression pipeline that estimates irrigation
water demand while retaining the deterministic rule and operational engines.

The ML output is advisory. It never directly controls irrigation hardware, and
this prototype is not a validated agronomic production model.

## Project evolution

```text
V0.1  Rule-Based Irrigation Engine
V0.2  Sensor Simulation + Operational Feasibility
V0.3  SQLite Persistence + Historical Memory
V0.4  Machine-Learning Irrigation Prediction
```

## V0.4 architecture

```text
                         FarmInput
                            ↓
             ┌──────────────┴──────────────┐
             ↓                             ↓
    Rule-Based Engine               Trained ML Pipeline
             ↓                             ↓
    Primary recommendation           Advisory prediction
             └──────────────┬──────────────┘
                            ↓
                     Comparison display
                            ↓
                   Operational Engine
                            ↓
                       Final action
```

The rule engine remains the deterministic safety and business-logic layer. The
ML model predicts likely water demand. Sensor reliability, pump availability,
and stored water still determine whether the rule recommendation can execute.

## Synthetic training data

V0.4 does not have years of real farm history, so it generates at least 1,000
deterministic synthetic rows using a fixed random seed. **These rows are
prototype examples, not real agricultural observations.**

Features include soil moisture, temperature, humidity, rain probability, field
area, crop, and crop stage. The target formula combines crop water rates with a
moisture-deficit factor, temperature, humidity, rainfall, crop stage, and small
controlled noise. This is richer than simply copying the V0.1 rules but remains
transparent and reproducible.

```text
Synthetic Data
      ↓
Train/Test Split
      ↓
Pipeline preprocessing (training portion only)
      ↓
Linear Regression + Random Forest training
      ↓
MAE, RMSE, and R² evaluation
      ↓
Save the better complete pipeline
      ↓
New FarmInput → advisory prediction
```

The split occurs before preprocessing is fitted. This prevents information from
the test set leaking into model training.

## Training versus inference

**Training** means learning patterns from historical examples. The training
command generates data, splits it, fits both models, evaluates them, and saves
the better complete pipeline.

**Inference** means loading that saved pipeline and using it to predict water
for one new farm condition. `main.py` performs inference; it does not silently
retrain the model.

## Train the model

Install the three direct dependencies and run training:

```powershell
python -m pip install -r requirements.txt
python -m app.ml.train
```

Training creates local generated artifacts:

```text
data/training_data.csv
artifacts/irrigation_model.joblib
```

Both are ignored by Git because they are reproducible build artifacts. If the
model is missing, the application clearly asks you to run the training command.

## Run Pushan and its tests

```powershell
python main.py
python -m unittest discover -s tests
```

The FIELD_001 demonstration displays its current sensors, the rule-based water
recommendation, the ML advisory estimate, their absolute and percentage
difference, and the final operational action. V0.3 SQLite history continues to
store the sensor reading, deterministic recommendation, and operational action.

## ML modules

- `app/ml/data_generator.py`: creates and saves reproducible synthetic data.
- `app/ml/train.py`: builds preprocessing, trains both regressors, evaluates
  them, selects the better model by RMSE then MAE, and saves the pipeline.
- `app/ml/predict.py`: loads the saved pipeline and predicts non-negative litres.
- `tests/test_ml.py`: tests data, training, persistence, prediction, and backward
  compatibility using a smaller temporary model.

## Existing persistence

V0.3 functionality remains: `fields`, `sensor_readings`,
`irrigation_decisions`, and `operational_actions` are stored in SQLite. The ML
estimate is currently a displayed advisory rather than a persisted action.

## Limitations and possible V0.5 direction

The model learns from synthetic data, so its metrics measure performance on the
same synthetic relationship—not real-world agronomic validity. It must not
operate pumps directly. A logical V0.5 could introduce versioned model metadata,
prediction logging and monitoring, and evaluation against carefully governed
real observations before any production use. No V0.5 features are included.
