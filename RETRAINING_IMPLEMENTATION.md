# Model Retraining Implementation Guide

## Overview

The "Initiate Retraining Cycle" button is now fully wired to the new trainable model, enabling the platform to learn from experimental data. This implementation includes before/after evaluation metrics and automatic model versioning.

## Architecture Changes

### 1. Enhanced Feedback Layer (`app/layers/feedback_layer.py`)

#### New Methods:

**`_compute_evaluation_metrics(y_true, y_pred, metric_name)`**

- Computes MAE, RMSE, R², and Pearson correlation
- Returns metrics dict with sample count
- Handles edge cases (insufficient data, zero variance)

**`evaluate_model_on_experiments(experiments, prediction_layer)`**

- Evaluates model on held-out or complete experiment set
- Computes metrics for activity, selectivity, stability separately
- Returns overall MAE and R² for dashboard display

**`trigger_model_retraining(new_experiments, trigger_reason, eval_experiments)`**

- Enhanced with before/after evaluation
- Filters quality experiments (≥3 required)
- Splits data: 80% training, 20% evaluation (if ≥10 experiments)
- Calls `prediction_layer.train()` to actually train the model
- Computes improvement metrics (MAE improvement %, R² improvement)
- Returns comprehensive job report with evaluation data

### 2. Updated Experiments Endpoint (`app/api/experiments.py`)

#### Enhanced `/trigger-retraining` POST endpoint:

**Request:**

```json
{
  "new_experiments": [...],
  "trigger_reason": "new_data",
  "use_all_quality_experiments": false
}
```

**Features:**

- Can auto-fetch all quality experiments from database
- Splits into training/evaluation sets for held-out testing
- Returns before-vs-after metrics for visualization
- Includes chart data with MAE and R² improvements
- Provides human-readable next steps

**Response:**

```json
{
  "success": true,
  "retraining_job": {
    "job_id": "retrain_20260511...",
    "version": "v2.1-trained",
    "status": "completed",
    "training_samples": 8
  },
  "evaluation": {
    "before": {
      "overall_mae": 12.4,
      "overall_r2": 0.68,
      "activity": {...},
      "selectivity": {...},
      "stability": {...}
    },
    "after": {
      "overall_mae": 8.1,
      "overall_r2": 0.82,
      ...
    },
    "improvement": {
      "mae_improvement": 4.3,
      "mae_percent_change": 34.68,
      "r2_improvement": 0.14,
      "r2_percent_change": 20.59
    }
  },
  "chart_data": {
    "metrics": ["MAE", "R²"],
    "before": {"MAE": 12.4, "R²": 0.68},
    "after": {"MAE": 8.1, "R²": 0.82}
  },
  "next_steps": [
    "New model version v2.1-trained trained and deployed",
    "Predictions will now reflect updated model",
    "Monitor re-ranking of catalysts on the dashboard"
  ]
}
```

#### New `/model-evaluation` GET endpoint:

**Purpose:** Fetch latest model evaluation metrics for dashboard visualization

**Response:**

```json
{
  "status": "success",
  "current_model": {
    "current_version": "v2.1-trained",
    "training_samples": 8,
    "status": "active",
    "accuracy_score": 0.82,
    "accuracy_improvement": 0.14,
    "created_at": "2026-05-11T10:30:00..."
  },
  "history": [
    {
      "version": "v2.1-trained",
      "accuracy": 0.82,
      "accuracy_improvement": 0.14,
      "training_samples": 8,
      "created_at": "..."
    }
  ],
  "model_improved": true
}
```

### 3. Updated Predictions Endpoint (`app/api/predictions.py`)

#### New Function: `ensure_latest_model()`

- Reloads model state from disk before each prediction
- Ensures every prediction uses the latest trained model
- Called automatically in `/rank` and `/predict-single` endpoints

#### Enhanced `/rank` POST endpoint:

- Calls `ensure_latest_model()` to load latest model
- Returns model training status in response:
  ```json
  {
    "model_info": {
      "version": "v2.1-trained",
      "is_trained": true,
      "training_samples": 8
    }
  }
  ```

#### Enhanced `/predict-single` POST endpoint:

- Automatically uses latest trained model
- Indicates in response whether model is trained or using physics-only

#### Updated `/model-info` GET endpoint:

- Shows trainable model metadata
- Indicates if model state was loaded from disk

## Workflow: End-to-End Retraining

### Step 1: Log Experiment Results

User logs a lab result via `/experiments/log-results`:

```
POST /api/experiments/log-results
{
  "reaction_id": "eth_jet",
  "catalyst_id": "cat_001",
  "measured_properties": {"activity": 65, "selectivity": 92, "stability": 78},
  "predicted_properties": {"activity": 60, "selectivity": 88, "stability": 75},
  "researcher_name": "Alice"
}
```

Response includes recommendation to trigger retraining if deviation is significant.

### Step 2: Trigger Retraining

User clicks "Initiate Retraining Cycle" button → calls `/trigger-retraining`:

```
POST /api/experiments/trigger-retraining
{
  "new_experiments": [
    {
      "catalyst_id": "cat_001",
      "measured_activity": 65,
      "measured_selectivity": 92,
      "measured_stability": 78,
      "predicted_activity": 60,
      "predicted_selectivity": 88,
      "predicted_stability": 75,
      "status": "normal"
    },
    ... (more experiments)
  ],
  "trigger_reason": "new_data",
  "use_all_quality_experiments": true
}
```

### Step 3: Model Evaluates Before Training

Feedback layer computes MAE and R² on evaluation set (20% held-out):

- Before: MAE = 12.4, R² = 0.68

### Step 4: Model Trains

Prediction layer trains linear regression models on physics-based features:

- Learns coefficients for activity, selectivity, stability
- Saves trained model to disk: `model_states/prediction_model_state.pkl`
- Updates version: v2.1-trained

### Step 5: Model Evaluates After Training

Feedback layer re-evaluates on same set:

- After: MAE = 8.1, R² = 0.82
- Improvement: 34.68% MAE reduction, 20.59% R² improvement

### Step 6: Dashboard Shows Results

Frontend displays bar chart:

```
MAE:        [Before: 12.4] → [After: 8.1] ↓ 34.68%
R²:         [Before: 0.68] → [After: 0.82] ↑ 20.59%

Model v2.1-trained trained on 6 experiments
```

### Step 7: Next Predictions Use New Model

When user clicks "Predict & Rank":

1. `/rank` endpoint calls `ensure_latest_model()`
2. TrainablePredictor loads model state from disk
3. Uses trained coefficients for predictions
4. Catalyst rankings may shift based on updated model

Example: Catalyst that was ranked #5 might now be ranked #3 if trained model corrects previous underprediction.

## Database Schema Updates

### ModelVersion table (already existed):

```python
class ModelVersion(Base):
    id: str (primary key)
    version: str              # e.g., "v2.1-trained"
    model_type: str          # "Linear Regression (Learnable)"
    status: str              # "active", "archived", "testing"
    trigger_reason: str      # "new_data", "accuracy_improvement", etc.
    training_samples: int    # Number of experiments used for training
    accuracy_score: float    # Final R² score after training
    accuracy_improvement: float  # R² improvement (after - before)
    training_started_at: datetime
    created_at: datetime
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ "Initiate Retraining" Button Clicked                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ POST /api/experiments/trigger-retraining                    │
│ - use_all_quality_experiments: true                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Fetch Quality Experiments from DB                           │
│ (status in ["normal", "verified_outperformer"])             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Split: 80% training, 20% evaluation                         │
│ (or all if < 10 experiments)                                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Evaluate Model BEFORE Training                              │
│ - Compute MAE, R² on evaluation set                         │
│ - Per-property metrics (activity, selectivity, stability)   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Train Prediction Layer                                      │
│ - prediction_layer.train(training_exps)                     │
│ - Fits LinearRegression on physics features                 │
│ - Saves model state to disk                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Evaluate Model AFTER Training                               │
│ - Compute MAE, R² on same evaluation set                    │
│ - Calculate improvement metrics                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Return Response with:                                       │
│ - Before/after metrics                                      │
│ - Improvement percentages                                   │
│ - Chart data (MAE, R²)                                      │
│ - Model version info                                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Frontend Displays Results                                   │
│ - Spinner: "Training new model…"                            │
│ - Chart: "Model v2.1 trained on 6 experiments"              │
│ - MAE improved from 12.4 to 8.1                             │
│ - R² improved from 0.68 to 0.82                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ User Clicks "Predict & Rank"                                │
│ POST /api/predictions/rank                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ ensure_latest_model() Loads Model from Disk                 │
│ - Reloads prediction_model_state.pkl                        │
│ - Uses trained coefficients                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│ Predict Properties & Rank Catalysts                         │
│ Rankings may have changed due to model update               │
└────────────────────────────────────────────────────────────┘
```

## Implementation Details

### Model Persistence

- **Save:** After training, `TrainablePredictor._save_model_state()` pickles:
  - model_version (incremented)
  - n_samples (training sample count)
  - is_trained (True after successful training)
  - sklearn LinearRegression objects (coefficients, intercept)
- **Load:** On startup or before prediction, `_load_model_state()` restores state from disk

- **Location:** `catalyst_m/model_states/prediction_model_state.pkl`

### Quality Gates

1. **Minimum samples:** Need ≥3 quality experiments to train
2. **Filtering:** Only "normal" and "verified_outperformer" experiments used
3. **Anomalies:** Excluded from training (they represent edge cases)
4. **Held-out eval:** 20% of data reserved for unbiased evaluation (if ≥10 samples)

### Feature Extraction

The trained model uses physics-informed features:

1. **d_band_centre** - weighted average d-band centre (eV)
2. **d_band_std** - standard deviation of d-band values
3. **avg_melting_point** - average melting point (K)
4. **num_elements** - number of distinct elements
5. **avg_electronegativity** - average electronegativity
6. **cu_fraction** - fraction of Cu in composition
7. **transition_metal_fraction** - fraction of transition metals

Each property (activity, selectivity, stability) gets its own LinearRegression model trained on these 7 features.

## API Usage Examples

### Example 1: Trigger Retraining with Specific Experiments

```bash
curl -X POST http://localhost:8000/api/experiments/trigger-retraining \
  -H "Content-Type: application/json" \
  -d '{
    "new_experiments": [
      {
        "catalyst_id": "cat_001",
        "measured_activity": 65,
        "measured_selectivity": 92,
        "measured_stability": 78,
        "predicted_activity": 60,
        "predicted_selectivity": 88,
        "predicted_stability": 75,
        "status": "normal"
      }
    ],
    "trigger_reason": "new_data"
  }'
```

### Example 2: Trigger Retraining with All DB Experiments

```bash
curl -X POST http://localhost:8000/api/experiments/trigger-retraining \
  -H "Content-Type: application/json" \
  -d '{
    "new_experiments": [],
    "trigger_reason": "new_data",
    "use_all_quality_experiments": true
  }'
```

### Example 3: Check Model Evaluation

```bash
curl -X GET http://localhost:8000/api/experiments/model-evaluation
```

### Example 4: Get Model Info

```bash
curl -X GET http://localhost:8000/api/predictions/model-info
```

### Example 5: Predict with Latest Model

```bash
curl -X POST http://localhost:8000/api/predictions/rank \
  -H "Content-Type: application/json" \
  -d '{
    "catalysts": [...],
    "reaction_conditions": {"temperature": 523.15, "pressure": 50.0},
    "reaction_id": "rxn_001"
  }'
```

Response will include:

```json
{
  "model_info": {
    "version": "v2.1-trained",
    "is_trained": true,
    "training_samples": 6
  }
}
```

## Testing Checklist

- [ ] Log experimental result via `/log-results`
- [ ] Verify experiment saved to DB with correct deviations
- [ ] Call `/trigger-retraining` with 5+ quality experiments
- [ ] Verify before/after metrics returned in response
- [ ] Check that MAE/R² improved (or stayed same)
- [ ] Confirm model version updated in DB
- [ ] Call `/model-evaluation` and verify metrics match
- [ ] Call `/predictions/rank` and verify uses trained model
- [ ] Confirm model_info shows is_trained=true
- [ ] Check that predictions differ from previous run (if model improved)
- [ ] Call `/retraining-history` and verify version recorded

## Performance Considerations

- **Training time:** ~100-500ms for typical experiment counts (5-20 samples)
- **Prediction latency:** +1-2ms per prediction (model loading from disk)
- **Model size:** ~50KB pickled (sklearn LinearRegression objects)
- **Memory:** ~5MB for prediction layer + trained models

## Future Enhancements

1. **Cross-validation:** Implement k-fold CV for better evaluation
2. **Feature selection:** Identify which features matter most
3. **Uncertainty quantification:** Return prediction uncertainty bands
4. **A/B testing:** Deploy new model alongside old for comparison
5. **Rollback:** Ability to revert to previous model version
6. **Scheduled retraining:** Automatic retraining on schedule
7. **Distributed training:** Support for larger datasets
8. **Model explainability:** Feature importance and SHAP values

## Troubleshooting

### Model not updating after retraining

- Check that `ensure_latest_model()` is being called in predictions endpoints
- Verify model file exists: `catalyst_m/model_states/prediction_model_state.pkl`
- Check logs for model loading errors

### Insufficient data for retraining

- Need minimum 3 quality experiments
- Anomalies are filtered out - verify experiments have correct status
- Use `/experiments/summary` to check experiment counts by status

### Predictions not changing after retraining

- Model was trained but evaluation metrics didn't show improvement (normal)
- Physics-informed heuristics may dominate for some catalysts
- Check response from `/predictions/model-info` to confirm model is trained

### Out of memory errors

- Reduce batch size in `/rank` endpoint
- Clear old model files from `model_states/`
- Check for memory leaks in long-running processes
