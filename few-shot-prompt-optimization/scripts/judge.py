#!/usr/bin/env python3
import argparse
import json
import os
import py_compile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_PATH = ROOT / "challenge.json"
PROGRESS_PATH = ROOT / "progress.json"
USER_ARTIFACTS_DIR = ROOT / "user_artifacts"


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
            item["milestone_id"] = milestone["id"]
            item["milestone_title"] = milestone["title"]
            yield item


def read_eda_summary():
    path = USER_ARTIFACTS_DIR / "eda_summary.json"
    if not path.exists():
        return None, [f"Missing artifact: {path.relative_to(ROOT)}"]
    try:
        return load_json(path), [f"Found artifact: {path.relative_to(ROOT)}"]
    except json.JSONDecodeError as exc:
        return None, [f"Invalid JSON in user_artifacts/eda_summary.json: {exc}"]


def present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def positive_number(value):
    return isinstance(value, (int, float)) and value > 0


def number_between_zero_and_one(value):
    return isinstance(value, (int, float)) and 0 <= value <= 1


def compile_python_artifact(path):
    try:
        py_compile.compile(str(path), cfile=os.devnull, doraise=True)
    except py_compile.PyCompileError as exc:
        return False, str(exc)
    return True, "Python artifact compiles."


def read_text(path):
    return path.read_text(encoding="utf-8")


def judge_eda_task(task):
    summary, evidence = read_eda_summary()
    missing_or_risky = []

    if summary is None:
        return "needs_revision", evidence, ["The EDA summary artifact is required for this task."]

    task_id = task["id"]
    if task_id == "row_count":
        ok = positive_number(summary.get("row_count"))
        evidence.append(f"row_count={summary.get('row_count')!r}")
        if not ok:
            missing_or_risky.append("row_count must be a positive number.")
    elif task_id == "splits":
        ok = present(summary.get("splits"))
        evidence.append(f"splits={summary.get('splits')!r}")
        if not ok:
            missing_or_risky.append("splits must list the available dataset splits.")
    elif task_id == "classes":
        ok = present(summary.get("classes"))
        evidence.append(f"classes count={len(summary.get('classes', [])) if isinstance(summary.get('classes'), list) else 'unknown'}")
        if not ok:
            missing_or_risky.append("classes must list at least one dataset label/class.")
    elif task_id == "messages":
        ok = present(summary.get("message_description"))
        evidence.append(f"message_description present={ok}")
        if not ok:
            missing_or_risky.append("message_description must describe what the utterances contain.")
    elif task_id == "average_length":
        ok = positive_number(summary.get("average_message_length"))
        evidence.append(f"average_message_length={summary.get('average_message_length')!r}")
        if not ok:
            missing_or_risky.append("average_message_length must be a positive number.")
    else:
        ok = False
        missing_or_risky.append(f"No dynamic judge rule is available for task {task_id!r}.")

    return ("pass" if ok else "needs_revision"), evidence, missing_or_risky


def judge_baseline_task(task):
    task_id = task["id"]
    evidence = []
    missing_or_risky = []

    if task_id == "baseline_classifier":
        path = USER_ARTIFACTS_DIR / "src" / "baseline.py"
        ok, message = compile_python_artifact(path)
        evidence.append(message)
        text = read_text(path) if path.exists() else ""
        has_classifier = "def " in text and ("classify" in text.lower() or "predict" in text.lower())
        mentions_intent = "intent" in text.lower()
        mentions_text_input = "text" in text.lower() or "utterance" in text.lower()
        if not has_classifier:
            missing_or_risky.append("baseline.py should define a classifier/predictor function.")
        if not mentions_intent:
            missing_or_risky.append("baseline.py should clearly classify ATIS intent labels.")
        if not mentions_text_input:
            missing_or_risky.append("baseline.py should accept or use the user utterance text.")
        return ("pass" if ok and has_classifier and mentions_intent and mentions_text_input else "needs_revision"), evidence, missing_or_risky

    if task_id == "metric_function":
        path = USER_ARTIFACTS_DIR / "src" / "metrics.py"
        ok, message = compile_python_artifact(path)
        evidence.append(message)
        text = read_text(path) if path.exists() else ""
        has_function = "def " in text
        mentions_expected = "expected" in text.lower() or "gold" in text.lower() or "label" in text.lower()
        mentions_predicted = "predicted" in text.lower() or "prediction" in text.lower()
        returns_binary = "return 1" in text or "return int(" in text or "return float(" in text
        if not has_function:
            missing_or_risky.append("metrics.py should define a reusable metric function.")
        if not mentions_expected or not mentions_predicted:
            missing_or_risky.append("Metric function should compare predicted and expected/gold labels.")
        if not returns_binary:
            missing_or_risky.append("Metric function should return a 0/1-style value.")
        return ("pass" if ok and has_function and mentions_expected and mentions_predicted and returns_binary else "needs_revision"), evidence, missing_or_risky

    if task_id == "baseline_score":
        path = USER_ARTIFACTS_DIR / "baseline_results.json"
        try:
            results = load_json(path)
        except json.JSONDecodeError as exc:
            return "needs_revision", [f"Invalid JSON in user_artifacts/baseline_results.json: {exc}"], []

        sample_size = results.get("sample_size")
        accuracy = results.get("accuracy")
        predictions = results.get("predictions")
        evidence.extend([
            f"sample_size={sample_size!r}",
            f"accuracy={accuracy!r}",
            f"predictions count={len(predictions) if isinstance(predictions, list) else 'unknown'}"
        ])
        if not positive_number(sample_size):
            missing_or_risky.append("baseline_results.json should include a positive sample_size.")
        if not number_between_zero_and_one(accuracy):
            missing_or_risky.append("baseline_results.json should include accuracy between 0 and 1.")
        if not isinstance(predictions, list) or not predictions:
            missing_or_risky.append("baseline_results.json should include a non-empty predictions list.")
        else:
            first = predictions[0]
            required = {"text", "gold_intent", "predicted_intent", "correct"}
            missing = sorted(required - set(first))
            if missing:
                missing_or_risky.append(f"Prediction rows should include keys: {', '.join(missing)}.")

        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    return "needs_revision", evidence, [f"No baseline judge rule is available for task {task_id!r}."]


def judge_task(task):
    evidence = [
        f"Task: {task['title']}",
        f"Milestone: {task['milestone_title']}",
        f"Judge level: {task.get('judge_level', 'medium')}"
    ]

    for artifact in task.get("expected_artifacts", []):
        artifact_path = ROOT / artifact
        if artifact_path.exists():
            evidence.append(f"Expected artifact exists: {artifact}")
        else:
            return {
                "verdict": "needs_revision",
                "confidence": "high",
                "evidence": evidence,
                "missing_or_risky": [f"Expected artifact is missing: {artifact}"],
                "commands_run": [],
                "checked_at": now()
            }

    if task["milestone_id"] == "eda":
        verdict, task_evidence, missing_or_risky = judge_eda_task(task)
        evidence.extend(task_evidence)
    elif task["milestone_id"] == "baseline":
        verdict, task_evidence, missing_or_risky = judge_baseline_task(task)
        evidence.extend(task_evidence)
    else:
        verdict = "needs_revision"
        missing_or_risky = ["This POC judge only knows how to evaluate the EDA and baseline milestones."]

    return {
        "verdict": verdict,
        "confidence": "medium" if verdict == "pass" else "high",
        "evidence": evidence,
        "missing_or_risky": missing_or_risky,
        "commands_run": [],
        "checked_at": now()
    }


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description="Judge BuildGuild challenge tasks.")
    parser.add_argument("--task", help="Judge a single task id.")
    parser.add_argument("--all", action="store_true", help="Judge all tasks, including pending tasks.")
    args = parser.parse_args()

    challenge = load_json(CHALLENGE_PATH)
    progress = load_json(PROGRESS_PATH)
    task_map = {task["id"]: task for task in iter_tasks(challenge)}

    judged = []
    for task_id, task in task_map.items():
        if args.task and task_id != args.task:
            continue

        state = progress["tasks"].setdefault(task_id, {
            "status": "pending",
            "builder_notes": "",
            "judge": None
        })

        if not args.all and state["status"] != "ready_for_judgment":
            continue

        judgment = judge_task(task)
        state["judge"] = judgment
        if judgment["verdict"] == "pass":
            state["status"] = "complete"
        else:
            state["status"] = "needs_revision"
        judged.append((task_id, judgment["verdict"]))

    save_json(PROGRESS_PATH, progress)

    if not judged:
        print("No tasks judged. Mark tasks as ready_for_judgment or pass --all.")
        return

    for task_id, verdict in judged:
        print(f"{task_id}: {verdict}")


if __name__ == "__main__":
    main()
