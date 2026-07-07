# Few-Shot Prompt Optimization

Build a simple prompt optimizer for ATIS intent classification.

This POC includes only the first milestone: quick EDA.

Learner-created outputs belong in `user_artifacts/`. Reusable examples and templates belong in `templates/`.

## Dataset

Use the Hugging Face dataset `tuetschek/atis`:

```python
from datasets import load_dataset

dataset = load_dataset("tuetschek/atis")
print(dataset)
print(dataset["train"][0])
```

Dataset page: https://huggingface.co/datasets/tuetschek/atis

For this challenge, use `text` as the user utterance and `intent` as the classification label. The dataset also includes `slots`, but slot tagging is not needed for the prompt-optimization task.

## Builder Flow

1. Read `challenge.json`.
2. Complete EDA work.
3. Save answers in `user_artifacts/eda_summary.json`. You can copy the starting shape from `templates/eda_summary.example.json`.
4. Update `progress.json` task statuses to `ready_for_judgment`.

You can mark a task ready with:

```bash
python scripts/mark_ready.py row_count --notes "Added row count to user_artifacts/eda_summary.json"
```

Or mark every task ready after completing the shared EDA artifact:

```bash
python scripts/mark_ready.py --milestone eda --notes "Completed user_artifacts/eda_summary.json"
```

For the baseline milestone, create:

- `user_artifacts/src/baseline.py`
- `user_artifacts/src/metrics.py`
- `user_artifacts/baseline_results.json`

Then mark the milestone ready:

```bash
python scripts/mark_ready.py --milestone baseline --notes "Completed baseline classifier, metric, and evaluation results"
```

The builder should not mark tasks complete.

## Judge Flow

Run:

```bash
python scripts/judge.py
```

The judge evaluates tasks that are `ready_for_judgment`, writes verdicts to `progress.json`, and marks passing tasks `complete`.

## Streamlit

Run:

```bash
streamlit run app.py
```
