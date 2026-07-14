# ATIS Few-Shot Optimization with DSPy

Optimize an ATIS intent classifier with DSPy, then export the compiled behavior to direct OpenAI code without requiring DSPy in production.

Learner-created files belong in `user_artifacts/`. Reusable examples belong in `templates/`.

## Builder flow

1. Read `challenge.json` and choose a pending milestone.
2. Complete its tasks and save the expected artifacts.
3. Mark the milestone ready, for example:

```bash
python scripts/mark_ready.py --milestone dspy_few_shot --notes "Compiled and evaluated the DSPy program"
```

4. Do not mark work complete. The judge owns completion.

Optional tasks such as MLflow do not block milestone completion and are skipped by `mark_ready.py --milestone` unless explicitly named.

## Judge flow

```bash
python scripts/judge.py
```

The judge evaluates every task currently marked `ready_for_judgment`.

## Streamlit

```bash
streamlit run app.py
```
