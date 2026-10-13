# ML Validation Benchmark

The benchmark evaluator measures task classification quality on labeled predictions. It is intentionally independent of model code so model versions can be compared using the same metric definition.

## Input

Use JSON or JSONL records with these fields:

```json
{"sample_id":"session-001-frame-0042","expected_task":"TASK-03","predicted_task":"TASK-03","confidence":0.94}
```

`expected_task` and `predicted_task` must be one of `TASK-01` through `TASK-06`.

## Run

From `apps/inference-service`:

```bash
python -m src.evaluation.benchmark validation/predictions.jsonl --output validation/report.json
```

The report contains accuracy, macro precision, macro recall, macro F1, and per-task support, predictions, true positives, precision, recall, and F1. Keep benchmark input labels separate from training data and record the model version alongside each run.