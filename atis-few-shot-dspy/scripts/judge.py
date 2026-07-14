#!/usr/bin/env python3
import argparse
import ast
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_PATH = ROOT / "challenge.json"
PROGRESS_PATH = ROOT / "progress.json"
ARTIFACTS = ROOT / "user_artifacts"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def iter_tasks(challenge):
    for milestone in challenge["milestones"]:
        for task in milestone["tasks"]:
            item = deepcopy(task)
            item["milestone_title"] = milestone["title"]
            yield item


def read_text(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def python_check(path):
    source = read_text(path)
    if not source:
        return False, f"Missing or empty Python file: {path.relative_to(ROOT)}"
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return False, f"Python syntax error: {exc}"
    return True, f"Python syntax is valid: {path.relative_to(ROOT)}"


def check_task(task):
    task_id = task["id"]
    evidence = []
    risks = []

    if task_id == "review_previous_quest":
        source = read_text(ARTIFACTS / "reuse_notes.md").lower()
        signals = sum(term in source for term in ("reuse", "adapt", "rebuild", "metric", "dataset", "evaluation", "self-contained"))
        ok = len(source) >= 180 and signals >= 3
        evidence.extend([f"Reuse notes length={len(source)}", f"Decision signals={signals}"])
        if not ok:
            risks.append("Document what will be reused, adapted, or rebuilt while keeping this quest self-contained.")
        return ok, evidence, risks

    if task_id == "create_classification_service":
        code_ok, message = python_check(ARTIFACTS / "src/service.py")
        source = read_text(ARTIFACTS / "src/service.py").lower()
        provider_signal = any(term in source for term in ("openai", "anthropic", "litellm", "client", "completion"))
        ok = code_ok and "def classify" in source and "message" in source and provider_signal
        evidence.extend([message, f"Stable classify interface={('def classify' in source)}", f"Provider call signal={provider_signal}"])
        if not ok:
            risks.append("Define classify(message: str) -> str and hide the provider call behind that interface.")
        return ok, evidence, risks

    if task_id == "smoke_test_service":
        result = load_json(ARTIFACTS / "service_smoke_test.json")
        rows = result.get("predictions") if isinstance(result, dict) else result
        row_ok = isinstance(rows, list) and len(rows) >= 3 and isinstance(rows[0], dict)
        row_ok = row_ok and "text" in rows[0] and ("predicted_intent" in rows[0] or "intent" in rows[0])
        evidence.append(f"Smoke-test predictions={len(rows) if isinstance(rows, list) else 0}")
        if not row_ok:
            risks.append("Save at least three message and predicted-intent pairs produced by the service.")
        return row_ok, evidence, risks

    if task_id == "create_dspy_splits":
        code_ok, message = python_check(ARTIFACTS / "src/prepare_dspy_data.py")
        manifest = load_json(ARTIFACTS / "split_manifest.json")
        source = read_text(ARTIFACTS / "src/prepare_dspy_data.py").lower()
        sizes_ok = all(isinstance(manifest.get(key), int) and manifest[key] > 0 for key in ("train_size", "test_size"))
        ok = code_ok and sizes_ok and manifest.get("seed") is not None and manifest.get("test_used_during_optimization") is False
        ok = ok and "dspy.example" in source and "with_inputs" in source
        evidence.extend([message, f"Seed={manifest.get('seed')!r}", f"Test excluded={manifest.get('test_used_during_optimization') is False}"])
        if not ok:
            risks.append("Create DSPy examples, fixed seeded splits, and keep test data out of optimization.")
        return ok, evidence, risks

    if task_id == "research_dspy_optimizers":
        source = read_text(ARTIFACTS / "optimizer_research.md").lower().replace(" ", "")
        names = ("bootstrapfewshot", "miprov2", "copro", "bootstrapfewshotwithrandomsearch", "simba")
        count = sum(name in source for name in names)
        ok = len(source) >= 450 and count >= 3 and ("http" in source or "documentation" in source)
        evidence.extend([f"Research length={len(source)}", f"Recognized optimizers={count}"])
        if not ok:
            risks.append("Compare at least three relevant optimizers and identify the source inspected.")
        return ok, evidence, risks

    if task_id == "compile_dspy_program":
        code_ok, message = python_check(ARTIFACTS / "src/optimize.py")
        run = load_json(ARTIFACTS / "optimization_run.json")
        source = read_text(ARTIFACTS / "src/optimize.py").lower()
        fields = (run.get("optimizer"), run.get("model"), run.get("seed"))
        ok = code_ok and "dspy" in source and "compile" in source and all(value is not None for value in fields)
        evidence.extend([message, f"Optimizer/model/seed={fields!r}"])
        if not ok:
            risks.append("Show a DSPy compile path and record optimizer, model, and seed.")
        return ok, evidence, risks

    if task_id == "save_best_program":
        saved = load_json(ARTIFACTS / "compiled_program.json")
        summary = read_text(ARTIFACTS / "compiled_program_summary.md").lower()
        ok = bool(saved) and len(summary) >= 250 and "instruction" in summary
        ok = ok and ("demo" in summary or "example" in summary) and ("output" in summary or "intent" in summary)
        evidence.extend([f"Saved top-level keys={sorted(saved)[:10]}", f"Summary length={len(summary)}"])
        if not ok:
            risks.append("Save program state and summarize its instructions, demonstrations, and output contract.")
        return ok, evidence, risks

    if task_id == "evaluate_dspy_test_set":
        result = load_json(ARTIFACTS / "dspy_test_results.json")
        rows = result.get("predictions")
        required = {"text", "gold_intent", "predicted_intent"}
        rows_ok = isinstance(rows, list) and bool(rows) and required.issubset(rows[0])
        accuracy = result.get("accuracy")
        ok = rows_ok and isinstance(accuracy, (int, float)) and 0 <= accuracy <= 1 and result.get("sample_size") == len(rows)
        evidence.extend([f"Sample size={result.get('sample_size')!r}", f"Accuracy={accuracy!r}"])
        if not ok:
            risks.append("Record valid accuracy and per-example held-out predictions.")
        return ok, evidence, risks

    if task_id == "add_mlflow":
        source = read_text(ARTIFACTS / "mlflow_notes.md").lower()
        ok = len(source) >= 150 and "mlflow" in source
        return ok, [f"MLflow notes length={len(source)}"], [] if ok else ["Describe what the MLflow integration records."]

    if task_id == "export_to_openai":
        code_ok, message = python_check(ARTIFACTS / "src/service.py")
        source = read_text(ARTIFACTS / "src/service.py").lower()
        ok = code_ok and "openai" in source and "def " in source and ("classif" in source or "predict" in source)
        evidence.append(message)
        reference_ok, reference_message = python_check(ARTIFACTS / "src/service_dspy_reference.py")
        ok = ok and reference_ok and "import dspy" not in source and "from dspy" not in source
        ok = ok and ("demo" in source or "example" in source or "instruction" in source)
        evidence.append(reference_message)
        if not ok:
            risks.append("Implement the OpenAI classifier; exported production code must encode compiled behavior without importing DSPy.")
        return ok, evidence, risks

    if task_id == "plan_dspy_export":
        source = read_text(ARTIFACTS / "export_plan.md").lower()
        signals = sum(term in source for term in ("instruction", "demo", "signature", "output", "service"))
        ok = len(source) >= 300 and signals >= 4
        evidence.extend([f"Plan length={len(source)}", f"Mapping signals={signals}"])
        if not ok:
            risks.append("Map instructions, demonstrations, signature, and output handling to the service interface.")
        return ok, evidence, risks

    if task_id == "test_export_alignment":
        result = load_json(ARTIFACTS / "alignment_results.json")
        rows = result.get("predictions")
        required = {"text", "gold_intent", "dspy_prediction", "openai_prediction", "agrees"}
        rows_ok = isinstance(rows, list) and bool(rows) and required.issubset(rows[0])
        accuracy_ok = all(isinstance(result.get(key), (int, float)) and 0 <= result[key] <= 1 for key in ("dspy_accuracy", "openai_accuracy"))
        alignment = result.get("alignment")
        ok = rows_ok and accuracy_ok and isinstance(alignment, (int, float)) and alignment >= 0.90
        ok = ok and result.get("sample_size") == len(rows)
        evidence.extend([f"Sample size={result.get('sample_size')!r}", f"Alignment={alignment!r}", f"DSPy/OpenAI accuracy={result.get('dspy_accuracy')!r}/{result.get('openai_accuracy')!r}"])
        if not ok:
            risks.append("Compare identical examples, reach 0.90 alignment, and report both accuracies.")
        return ok, evidence, risks

    return False, evidence, [f"No judge rule exists for {task_id}."]


def judge(task):
    evidence = [f"Task: {task['title']}", f"Milestone: {task['milestone_title']}", f"Judge level: {task.get('judge_level', 'medium')}"]
    missing = [artifact for artifact in task.get("expected_artifacts", []) if not (ROOT / artifact).exists()]
    if missing:
        return make_verdict(False, evidence, [f"Expected artifact is missing: {artifact}" for artifact in missing])
    evidence.extend(f"Found artifact: {artifact}" for artifact in task.get("expected_artifacts", []))
    try:
        ok, extra, risks = check_task(task)
    except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
        ok, extra, risks = False, [], [f"Could not inspect artifact: {exc}"]
    return make_verdict(ok, evidence + extra, risks)


def make_verdict(ok, evidence, risks):
    return {"verdict": "pass" if ok else "needs_revision", "confidence": "high", "evidence": evidence, "missing_or_risky": risks, "commands_run": [], "checked_at": datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description="Judge ATIS DSPy challenge tasks.")
    parser.add_argument("--task", help="Judge one task id.")
    parser.add_argument("--all", action="store_true", help="Judge all tasks, including pending tasks.")
    args = parser.parse_args()
    challenge = load_json(CHALLENGE_PATH)
    progress = load_json(PROGRESS_PATH)
    judged = []
    for task in iter_tasks(challenge):
        if args.task and task["id"] != args.task:
            continue
        state = progress["tasks"].setdefault(task["id"], {"status": "pending", "builder_notes": "", "judge": None})
        if not args.all and state["status"] != "ready_for_judgment":
            continue
        judgment = judge(task)
        state["judge"] = judgment
        state["status"] = "complete" if judgment["verdict"] == "pass" else "needs_revision"
        judged.append((task["id"], judgment["verdict"]))
    save_json(PROGRESS_PATH, progress)
    if not judged:
        print("No tasks judged. Mark tasks ready or pass --all.")
    for task_id, verdict in judged:
        print(f"{task_id}: {verdict}")


if __name__ == "__main__":
    main()
