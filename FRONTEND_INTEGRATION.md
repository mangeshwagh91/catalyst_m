# Frontend Integration Guide - Model Retraining

## Quick Start: Wiring the Button

### The "Initiate Retraining Cycle" Button Flow

#### 1. Button Click Handler

```typescript
async function handleInitiateRetraining() {
  setIsTraining(true);
  setProgressMessage("Training new model…");

  try {
    const response = await fetch("/api/experiments/trigger-retraining", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        new_experiments: [], // Empty = fetch from DB
        trigger_reason: "user_initiated",
        use_all_quality_experiments: true, // Fetch all quality experiments from DB
      }),
    });

    const data = await response.json();

    if (data.success) {
      // Show results
      displayRetrainingResults(data);
      setProgressMessage("Training complete!");
    } else {
      setProgressMessage(`Training failed: ${data.error}`);
    }
  } finally {
    setIsTraining(false);
  }
}
```

#### 2. Display Results Component

```typescript
interface RetrainingResults {
  retraining_job: {
    version: string;
    status: string;
    training_samples: number;
  };
  evaluation: {
    before: {
      overall_mae: number;
      overall_r2: number;
    };
    after: {
      overall_mae: number;
      overall_r2: number;
    };
    improvement: {
      mae_improvement: number;
      mae_percent_change: number;
      r2_improvement: number;
      r2_percent_change: number;
    };
  };
  chart_data: {
    metrics: string[];
    before: { [key: string]: number };
    after: { [key: string]: number };
  };
}

function RetrainingResultsCard({ results }: { results: RetrainingResults }) {
  return (
    <Card>
      <CardHeader>
        <h3>Model Retraining Complete</h3>
        <p className="text-sm text-gray-500">
          {results.retraining_job.version} trained on {results.retraining_job.training_samples} experiments
        </p>
      </CardHeader>

      <CardContent>
        {/* Before/After Bar Chart */}
        <div className="mb-6">
          <h4 className="font-semibold mb-4">Model Performance Improvement</h4>
          <BarChart
            data={[
              {
                metric: "MAE",
                before: results.chart_data.before.MAE,
                after: results.chart_data.after.MAE
              },
              {
                metric: "R²",
                before: results.chart_data.before.R2,
                after: results.chart_data.after.R2
              }
            ]}
          />
        </div>

        {/* Improvement Summary */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-green-50 rounded">
            <p className="text-sm text-gray-600">MAE Improvement</p>
            <p className="text-2xl font-bold text-green-600">
              {results.evaluation.improvement.mae_improvement.toFixed(1)}
            </p>
            <p className="text-xs text-green-600">
              {results.evaluation.improvement.mae_percent_change.toFixed(1)}% improvement
            </p>
          </div>

          <div className="p-4 bg-blue-50 rounded">
            <p className="text-sm text-gray-600">R² Improvement</p>
            <p className="text-2xl font-bold text-blue-600">
              {results.evaluation.improvement.r2_improvement.toFixed(3)}
            </p>
            <p className="text-xs text-blue-600">
              {results.evaluation.improvement.r2_percent_change.toFixed(1)}% improvement
            </p>
          </div>
        </div>

        {/* Before/After Metrics Table */}
        <table className="mt-6 w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2">Metric</th>
              <th className="text-right py-2">Before</th>
              <th className="text-right py-2">After</th>
              <th className="text-right py-2">Change</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b">
              <td className="py-2">MAE</td>
              <td className="text-right">{results.evaluation.before.overall_mae?.toFixed(2)}</td>
              <td className="text-right">{results.evaluation.after.overall_mae?.toFixed(2)}</td>
              <td className="text-right text-green-600">
                ↓ {results.evaluation.improvement.mae_improvement?.toFixed(2)}
              </td>
            </tr>
            <tr>
              <td className="py-2">R²</td>
              <td className="text-right">{results.evaluation.before.overall_r2?.toFixed(3)}</td>
              <td className="text-right">{results.evaluation.after.overall_r2?.toFixed(3)}</td>
              <td className="text-right text-green-600">
                ↑ {results.evaluation.improvement.r2_improvement?.toFixed(3)}
              </td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
```

### 3. Dashboard Update Flow

After retraining completes, update the dashboard:

```typescript
// 1. Show completion message with model version
<Alert variant="success">
  Model {results.retraining_job.version} trained on {results.retraining_job.training_samples}
  experiments — MAE improved from {results.evaluation.before.overall_mae?.toFixed(1)} to
  {results.evaluation.after.overall_mae?.toFixed(1)}
</Alert>

// 2. Display chart
<RetrainingResultsCard results={results} />

// 3. Trigger re-ranking
<Button onClick={handleReRankCatalysts}>
  Re-Rank Catalysts with Updated Model
</Button>
```

### 4. Get Model Evaluation for Monitoring Tab

```typescript
async function loadModelEvaluation() {
  try {
    const response = await fetch("/api/experiments/model-evaluation");
    const data = await response.json();

    if (data.status === "success") {
      setModelMetrics({
        currentVersion: data.current_model.current_version,
        trainingPct: data.current_model.training_samples,
        accuracyScore: data.current_model.accuracy_score,
        accuracyImprovement: data.current_model.accuracy_improvement,
        modelImproved: data.model_improved,
        history: data.history,
      });
    }
  } catch (error) {
    console.error("Failed to load model evaluation:", error);
  }
}
```

## UI Components to Build

### 1. Retraining Status Modal

```
┌─────────────────────────────────────────┐
│ Training New Model                 [×]  │
├─────────────────────────────────────────┤
│                                         │
│  [◐] Training new model…                │
│                                         │
│  Processing 6 quality experiments       │
│  Splitting: 5 train / 1 evaluation      │
│                                         │
│  Step 1/3: Evaluating baseline model... │
│  Step 2/3: Training on new data...      │
│  Step 3/3: Evaluating updated model...  │
│                                         │
│                           [Cancel]     │
└─────────────────────────────────────────┘
```

### 2. Results Card

```
┌──────────────────────────────────────────────┐
│ Model v2.1-trained Training Complete         │
│ Trained on 6 experiments                     │
├──────────────────────────────────────────────┤
│                                              │
│  Model Performance Improvement               │
│  ┌─────────────┬─────────────┐             │
│  │     MAE     │      R²     │             │
│  ├─────────────┼─────────────┤             │
│  │ Before: 12.4│ Before: 0.68│             │
│  │ After:  8.1 │ After:  0.82│             │
│  │ ↓34.7%      │ ↑20.6%      │             │
│  └─────────────┴─────────────┘             │
│                                              │
│  MAE Improvement: 4.3 (34.7% ↓)             │
│  R² Improvement: 0.14 (20.6% ↑)             │
│                                              │
│  [Re-Rank Catalysts] [View Details]        │
└──────────────────────────────────────────────┘
```

### 3. Model Monitoring Dashboard

```
┌──────────────────────────────────────────────┐
│ Model Training History                       │
├──────────────────────────────────────────────┤
│                                              │
│ Current Version: v2.1-trained               │
│ Status: Active                               │
│ Trained on: 6 experiments                    │
│ Accuracy (R²): 0.82                          │
│ Last Updated: 2026-05-11 10:30 AM           │
│                                              │
│ Version History:                             │
│ ┌──────────────┬──────────┬──────────┐     │
│ │ Version      │ R² Score │ Samples  │     │
│ ├──────────────┼──────────┼──────────┤     │
│ │ v2.1-trained │   0.82   │    6     │     │
│ │ v2.0-trained │   0.78   │    4     │     │
│ │ v1.0-physics │   0.65   │    -     │     │
│ └──────────────┴──────────┴──────────┘     │
│                                              │
└──────────────────────────────────────────────┘
```

## API Endpoints Summary

### Trigger Retraining

```
POST /api/experiments/trigger-retraining

Request:
{
  "new_experiments": [],
  "trigger_reason": "user_initiated",
  "use_all_quality_experiments": true
}

Response:
{
  "success": true,
  "retraining_job": { ... },
  "evaluation": {
    "before": { "overall_mae": 12.4, "overall_r2": 0.68 },
    "after": { "overall_mae": 8.1, "overall_r2": 0.82 },
    "improvement": { "mae_improvement": 4.3, "mae_percent_change": 34.68, ... }
  },
  "chart_data": { ... },
  "next_steps": [...]
}
```

### Get Model Evaluation

```
GET /api/experiments/model-evaluation

Response:
{
  "status": "success",
  "current_model": {
    "current_version": "v2.1-trained",
    "accuracy_score": 0.82,
    "accuracy_improvement": 0.14,
    "training_samples": 6
  },
  "history": [...],
  "model_improved": true
}
```

### Get Model Info

```
GET /api/predictions/model-info

Response:
{
  "version": "v2.1-trained",
  "trainable_model_info": {
    "is_trained": true,
    "n_training_samples": 6
  }
}
```

### Make Predictions (Updated)

```
POST /api/predictions/rank

Response includes:
{
  "model_info": {
    "version": "v2.1-trained",
    "is_trained": true,
    "training_samples": 6
  },
  "predictions": [...]
}
```

## Workflow Integration Points

### 1. Feedback Loop Tab - Retraining Section

- **Trigger:** "Initiate Retraining Cycle" button
- **Status:** Show spinner with "Training new model…"
- **Results:** Display before-vs-after bar chart
- **Action:** "Re-Rank Catalysts" button becomes enabled

### 2. Dashboard - Model Info Box

- **Display:** Current model version
- **Metric:** R² score and improvement
- **Update:** Refresh after successful retraining
- **Link:** "View Full History" → model-evaluation endpoint

### 3. Prediction Results - Model Source

- **Show:** "Model v2.1-trained (8 training samples)"
- **Indicator:** ✓ Trained model / ⚙ Physics-based
- **Info:** Accuracy metrics if trained

### 4. Experiment Table - Status Column

- **Filter:** Show only "normal" and "verified_outperformer" for training
- **Flag:** "Included in latest retraining" badge

## Expected User Experience

1. **User logs 5+ experiments** over time
2. **"Initiate Retraining" button becomes enabled** (green)
3. **User clicks button** → spinner shows "Training new model…"
4. **After ~2-5 seconds** → results appear:
   - "Model v2.1 trained on 6 experiments"
   - Chart shows "MAE improved from 12.4 to 8.1"
   - "R² improved from 0.68 to 0.82"
5. **User clicks "Re-Rank Catalysts"**
6. **Catalyst rankings update** (some may shift positions)
7. **Dashboard shows new model version** as active

## Error Handling

### Insufficient Data

```
Response: 400 Bad Request
{
  "success": false,
  "error": "Need at least 3 quality experiments, got 2",
  "n_experiments": 2
}

UI: Show alert "Need at least 3 logged experiments to retrain model"
```

### Model Training Failed

```
Response: 500 Internal Server Error
{
  "detail": "Model training error: ..."
}

UI: Show error alert with retry button
```

### No Trained Models Yet

```
GET /api/experiments/model-evaluation
{
  "status": "no_models",
  "message": "No trained models found. Retraining is required."
}

UI: Show info "Awaiting first retraining cycle"
```

## Testing Checklist

- [ ] Log 6 experiments via the UI
- [ ] Verify they appear in Feedback Loop tab
- [ ] Click "Initiate Retraining" button
- [ ] Verify spinner shows "Training new model…"
- [ ] Verify results card displays before/after metrics
- [ ] Verify chart shows MAE and R² improvements
- [ ] Click "Re-Rank Catalysts"
- [ ] Verify predictions use new model (check `/predictions/model-info`)
- [ ] Verify some catalyst rankings changed
- [ ] Refresh page and verify model version persists
- [ ] Check model history shows version progression

## Performance Tips

1. **Debounce re-ranking:** Don't allow rapid clicks after retraining
2. **Cache model evaluation:** Load `/model-evaluation` on component mount
3. **Async status polling:** Show spinner until response returns
4. **Batch experiment logging:** Log multiple experiments before retraining
5. **Lazy load history:** Only load full history when user clicks "View Details"

## Accessibility

- Ensure button is keyboard accessible
- Announce progress updates to screen readers: "Training started", "Training complete"
- Use semantic HTML for results table
- Ensure chart has text fallback with metrics
- Color contrast for before/after metrics
