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

    if task_id == "baseline_prompt":
        path = USER_ARTIFACTS_DIR / "prompts" / "baseline_prompt.txt"
        text = read_text(path) if path.exists() else ""
        lower = text.lower()
        mentions_message = "message" in lower or "utterance" in lower or "{text}" in lower
        mentions_label = "label" in lower or "intent" in lower or "{labels}" in lower
        instructs_single = "return only" in lower or "exactly one" in lower or "single" in lower
        evidence.extend([
            f"prompt length={len(text)}",
            f"mentions message={mentions_message}",
            f"mentions label/intent={mentions_label}"
        ])
        if not text.strip():
            missing_or_risky.append("baseline_prompt.txt should not be empty.")
        if not mentions_message:
            missing_or_risky.append("Prompt should include or reference the ATIS message text.")
        if not mentions_label:
            missing_or_risky.append("Prompt should ask for an intent label/class.")
        if not instructs_single:
            missing_or_risky.append("Prompt should constrain the model to one label or a minimal output.")
        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    if task_id == "single_message_classifier":
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


def judge_naive_optimizer_task(task):
    task_id = task["id"]
    evidence = []
    missing_or_risky = []

    if task_id == "fewshot_prompt_section":
        path = USER_ARTIFACTS_DIR / "prompts" / "fewshot_prompt_template.txt"
        text = read_text(path) if path.exists() else ""
        lower = text.lower()
        has_examples_language = "example" in lower or "few-shot" in lower or "few shot" in lower
        has_marker = "{{" in text or "}}" in text or "few_shot" in lower or "fewshot" in lower
        has_separator = "---" in text or "separator" in lower or "example" in lower
        evidence.extend([
            f"template length={len(text)}",
            f"mentions examples={has_examples_language}",
            f"has insertion marker={has_marker}",
            f"has separator cue={has_separator}"
        ])
        if not text.strip():
            missing_or_risky.append("fewshot_prompt_template.txt should not be empty.")
        if not has_examples_language:
            missing_or_risky.append("Prompt template should mention examples or few-shot guidance.")
        if not has_marker:
            missing_or_risky.append("Prompt template should include a unique insertion marker for examples.")
        if not has_separator:
            missing_or_risky.append("Prompt template should include or imply a consistent example separator.")
        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    if task_id == "naive_fewshot_optimizer":
        path = USER_ARTIFACTS_DIR / "src" / "naive_optimizer.py"
        ok, message = compile_python_artifact(path)
        evidence.append(message)
        text = read_text(path) if path.exists() else ""
        lower = text.lower()
        has_function = "def " in text
        mentions_train = "train" in lower
        mentions_count = "num" in lower or "count" in lower or "k=" in lower
        uses_random = "random" in lower or "sample" in lower or "shuffle" in lower
        builds_prompt = "prompt" in lower and ("return" in lower or "replace" in lower or "join" in lower)
        evidence.extend([
            f"defines function={has_function}",
            f"mentions train examples={mentions_train}",
            f"mentions desired count={mentions_count}",
            f"uses randomization={uses_random}",
            f"builds prompt={builds_prompt}"
        ])
        if not has_function:
            missing_or_risky.append("naive_optimizer.py should define a reusable function.")
        if not mentions_train:
            missing_or_risky.append("Optimizer should accept or use train examples.")
        if not mentions_count:
            missing_or_risky.append("Optimizer should accept or use the desired number of examples.")
        if not uses_random:
            missing_or_risky.append("Optimizer should randomly sample or shuffle examples.")
        if not builds_prompt:
            missing_or_risky.append("Optimizer should construct and return a prompt string.")
        return ("pass" if ok and not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    return "needs_revision", evidence, [f"No naive optimizer judge rule is available for task {task_id!r}."]


def judge_results_json(path, artifact_name):
    try:
        results = load_json(path)
    except json.JSONDecodeError as exc:
        return None, [f"Invalid JSON in {artifact_name}: {exc}"], [f"{artifact_name} must be valid JSON."]

    evidence = []
    missing_or_risky = []
    sample_size = results.get("sample_size")
    accuracy = results.get("accuracy")
    predictions = results.get("predictions")
    evidence.extend([
        f"sample_size={sample_size!r}",
        f"accuracy={accuracy!r}",
        f"predictions count={len(predictions) if isinstance(predictions, list) else 'unknown'}"
    ])
    if not positive_number(sample_size):
        missing_or_risky.append(f"{artifact_name} should include a positive sample_size.")
    if not number_between_zero_and_one(accuracy):
        missing_or_risky.append(f"{artifact_name} should include accuracy between 0 and 1.")
    if not isinstance(predictions, list) or not predictions:
        missing_or_risky.append(f"{artifact_name} should include a non-empty predictions list.")
    else:
        first = predictions[0]
        required = {"text", "gold_intent", "predicted_intent", "correct"}
        missing = sorted(required - set(first))
        if missing:
            missing_or_risky.append(f"Prediction rows should include keys: {', '.join(missing)}.")
    return results, evidence, missing_or_risky


def judge_naive_prompt_evaluation_task(task):
    task_id = task["id"]
    evidence = []
    missing_or_risky = []

    if task_id == "generate_naive_prompt":
        path = USER_ARTIFACTS_DIR / "prompts" / "naive_fewshot_prompt.txt"
        text = read_text(path) if path.exists() else ""
        lower = text.lower()
        has_examples = "example" in lower or "---" in text or "intent:" in lower
        has_message_instruction = "message" in lower or "utterance" in lower or "{text}" in lower
        has_label_instruction = "intent" in lower or "label" in lower
        has_empty_marker = "{{few_shot_examples}}" in lower or "{{fewshot" in lower
        evidence.extend([
            f"prompt length={len(text)}",
            f"has inserted examples={has_examples}",
            f"has message instruction={has_message_instruction}",
            f"has label instruction={has_label_instruction}"
        ])
        if not text.strip():
            missing_or_risky.append("naive_fewshot_prompt.txt should not be empty.")
        if not has_examples:
            missing_or_risky.append("Generated prompt should show evidence of inserted few-shot examples.")
        if not has_message_instruction:
            missing_or_risky.append("Generated prompt should include the message/classification instruction.")
        if not has_label_instruction:
            missing_or_risky.append("Generated prompt should ask for an intent label.")
        if has_empty_marker:
            missing_or_risky.append("Generated prompt still appears to contain an unfilled few-shot placeholder.")
        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    if task_id == "evaluate_naive_prompt":
        path = USER_ARTIFACTS_DIR / "naive_fewshot_results.json"
        _, result_evidence, result_missing = judge_results_json(path, "user_artifacts/naive_fewshot_results.json")
        evidence.extend(result_evidence)
        missing_or_risky.extend(result_missing)
        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    if task_id == "compare_to_baseline":
        path = USER_ARTIFACTS_DIR / "naive_vs_baseline.json"
        try:
            comparison = load_json(path)
        except json.JSONDecodeError as exc:
            return "needs_revision", [f"Invalid JSON in user_artifacts/naive_vs_baseline.json: {exc}"], []

        baseline_accuracy = comparison.get("baseline_accuracy")
        naive_accuracy = comparison.get("naive_fewshot_accuracy")
        delta = comparison.get("delta")
        outcome = comparison.get("outcome")
        has_comparison = outcome is not None or delta is not None or comparison.get("improved") is not None
        evidence.extend([
            f"baseline_accuracy={baseline_accuracy!r}",
            f"naive_fewshot_accuracy={naive_accuracy!r}",
            f"delta={delta!r}",
            f"outcome={outcome!r}"
        ])
        if not number_between_zero_and_one(baseline_accuracy):
            missing_or_risky.append("naive_vs_baseline.json should include baseline_accuracy between 0 and 1.")
        if not number_between_zero_and_one(naive_accuracy):
            missing_or_risky.append("naive_vs_baseline.json should include naive_fewshot_accuracy between 0 and 1.")
        if not has_comparison:
            missing_or_risky.append("naive_vs_baseline.json should include delta, outcome, or improved.")
        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    return "needs_revision", evidence, [f"No naive prompt evaluation judge rule is available for task {task_id!r}."]


def judge_multi_seed_optimizer_task(task):
    task_id = task["id"]
    evidence = []
    missing_or_risky = []

    if task_id in {"multi_seed_optimizer_function", "multi_seed_looping"}:
        path = USER_ARTIFACTS_DIR / "src" / "multi_seed_optimizer.py"
        ok, message = compile_python_artifact(path)
        evidence.append(message)
        text = read_text(path) if path.exists() else ""
        lower = text.lower()
        has_function = "def " in text
        mentions_train = "train" in lower
        mentions_dev = "dev" in lower or "validation" in lower
        mentions_examples_count = "num_examples" in lower or "n_examples" in lower or "example_count" in lower
        mentions_loop_count = "num_loops" in lower or "n_loops" in lower or "trials" in lower or "range(" in lower
        uses_seed = "seed" in lower
        uses_randomization = "random" in lower or "sample" in lower or "shuffle" in lower

        evidence.extend([
            f"defines function={has_function}",
            f"mentions train examples={mentions_train}",
            f"mentions dev examples={mentions_dev}",
            f"mentions example count={mentions_examples_count}",
            f"mentions loop count={mentions_loop_count}",
            f"uses seed={uses_seed}",
            f"uses randomization={uses_randomization}"
        ])

        if not has_function:
            missing_or_risky.append("multi_seed_optimizer.py should define a reusable optimizer function.")
        if not mentions_train:
            missing_or_risky.append("Optimizer should accept or use train examples.")
        if not mentions_dev:
            missing_or_risky.append("Optimizer should accept or use dev examples.")
        if not mentions_examples_count:
            missing_or_risky.append("Optimizer should accept or use the desired number of few-shot examples.")
        if not mentions_loop_count:
            missing_or_risky.append("Optimizer should accept or use a loop/trial count.")

        if task_id == "multi_seed_looping":
            if not uses_seed:
                missing_or_risky.append("Looping logic should use different seeds or record seed values.")
            if not uses_randomization:
                missing_or_risky.append("Looping logic should randomize candidate few-shot sets.")

        return ("pass" if ok and not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    if task_id == "multi_seed_dev_evaluation":
        code_path = USER_ARTIFACTS_DIR / "src" / "multi_seed_optimizer.py"
        code_text = read_text(code_path) if code_path.exists() else ""
        code_lower = code_text.lower()
        mentions_evaluation = "evaluate" in code_lower or "metric" in code_lower or "score" in code_lower
        mentions_best = "best" in code_lower or "min(" in code_lower or "max(" in code_lower

        path = USER_ARTIFACTS_DIR / "multi_seed_optimizer_results.json"
        try:
            results = load_json(path)
        except json.JSONDecodeError as exc:
            return "needs_revision", [f"Invalid JSON in user_artifacts/multi_seed_optimizer_results.json: {exc}"], []

        num_loops = results.get("num_loops")
        best_score = results.get("best_score")
        best_seed = results.get("best_seed")
        trials = results.get("trials")
        selection_mode = results.get("selection_mode")
        evidence.extend([
            f"code mentions evaluation={mentions_evaluation}",
            f"code mentions best selection={mentions_best}",
            f"num_loops={num_loops!r}",
            f"best_score={best_score!r}",
            f"best_seed={best_seed!r}",
            f"selection_mode={selection_mode!r}",
            f"trials count={len(trials) if isinstance(trials, list) else 'unknown'}"
        ])

        if not mentions_evaluation:
            missing_or_risky.append("Optimizer code should evaluate candidate prompts on dev examples.")
        if not mentions_best:
            missing_or_risky.append("Optimizer code should keep the best candidate, not just the final candidate.")
        if not positive_number(num_loops):
            missing_or_risky.append("multi_seed_optimizer_results.json should include a positive num_loops.")
        if not isinstance(best_score, (int, float)):
            missing_or_risky.append("multi_seed_optimizer_results.json should include numeric best_score.")
        if best_seed is None:
            missing_or_risky.append("multi_seed_optimizer_results.json should include best_seed.")
        if selection_mode not in {"min", "max", "lowest", "highest"}:
            missing_or_risky.append("multi_seed_optimizer_results.json should include selection_mode such as min or max.")
        if not isinstance(trials, list) or not trials:
            missing_or_risky.append("multi_seed_optimizer_results.json should include a non-empty trials list.")
        else:
            first = trials[0]
            required = {"seed", "score"}
            missing = sorted(required - set(first))
            if missing:
                missing_or_risky.append(f"Trial rows should include keys: {', '.join(missing)}.")

        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    return "needs_revision", evidence, [f"No multi-seed optimizer judge rule is available for task {task_id!r}."]


def judge_optimizer_reuse_task(task):
    task_id = task["id"]
    evidence = []
    missing_or_risky = []

    if task_id == "reuse_naive_optimizer":
        multi_path = USER_ARTIFACTS_DIR / "src" / "multi_seed_optimizer.py"
        naive_path = USER_ARTIFACTS_DIR / "src" / "naive_optimizer.py"
        multi_ok, multi_message = compile_python_artifact(multi_path)
        naive_ok, naive_message = compile_python_artifact(naive_path)
        evidence.extend([multi_message, naive_message])

        multi_text = read_text(multi_path) if multi_path.exists() else ""
        naive_text = read_text(naive_path) if naive_path.exists() else ""
        multi_lower = multi_text.lower()
        naive_lower = naive_text.lower()
        naive_has_function = "def " in naive_text and ("prompt" in naive_lower or "fewshot" in naive_lower or "few_shot" in naive_lower)
        imports_or_mentions_naive = "naive_optimizer" in multi_lower or "build_fewshot" in multi_lower or "build_few_shot" in multi_lower
        calls_prompt_builder = "build_fewshot" in multi_lower or "build_few_shot" in multi_lower or "naive" in multi_lower
        evidence.extend([
            f"naive optimizer has prompt function={naive_has_function}",
            f"multi-seed imports or mentions naive optimizer={imports_or_mentions_naive}",
            f"multi-seed calls prompt builder={calls_prompt_builder}"
        ])
        if not naive_has_function:
            missing_or_risky.append("naive_optimizer.py should still define the prompt-building function.")
        if not imports_or_mentions_naive:
            missing_or_risky.append("multi_seed_optimizer.py should import or explicitly reference the naive optimizer.")
        if not calls_prompt_builder:
            missing_or_risky.append("multi_seed_optimizer.py should call the naive prompt builder rather than duplicating it.")
        return ("pass" if multi_ok and naive_ok and not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    if task_id == "document_optimizer_reuse":
        path = USER_ARTIFACTS_DIR / "optimizer_reuse_notes.md"
        text = read_text(path) if path.exists() else ""
        lower = text.lower()
        mentions_naive = "naive" in lower
        mentions_multi_seed = "multi" in lower or "sophisticated" in lower
        mentions_responsibility = "responsib" in lower or "split" in lower or "reuse" in lower
        evidence.extend([
            f"notes length={len(text)}",
            f"mentions naive optimizer={mentions_naive}",
            f"mentions multi-seed optimizer={mentions_multi_seed}",
            f"mentions responsibility/reuse={mentions_responsibility}"
        ])
        if not text.strip():
            missing_or_risky.append("optimizer_reuse_notes.md should not be empty.")
        if not mentions_naive:
            missing_or_risky.append("Notes should mention the naive optimizer.")
        if not mentions_multi_seed:
            missing_or_risky.append("Notes should mention the multi-seed/sophisticated optimizer.")
        if not mentions_responsibility:
            missing_or_risky.append("Notes should explain the reuse or responsibility split.")
        return ("pass" if not missing_or_risky else "needs_revision"), evidence, missing_or_risky

    return "needs_revision", evidence, [f"No optimizer reuse judge rule is available for task {task_id!r}."]


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
    elif task["milestone_id"] == "naive_optimizer":
        verdict, task_evidence, missing_or_risky = judge_naive_optimizer_task(task)
        evidence.extend(task_evidence)
    elif task["milestone_id"] == "naive_prompt_evaluation":
        verdict, task_evidence, missing_or_risky = judge_naive_prompt_evaluation_task(task)
        evidence.extend(task_evidence)
    elif task["milestone_id"] == "multi_seed_optimizer":
        verdict, task_evidence, missing_or_risky = judge_multi_seed_optimizer_task(task)
        evidence.extend(task_evidence)
    elif task["milestone_id"] == "optimizer_reuse_refactor":
        verdict, task_evidence, missing_or_risky = judge_optimizer_reuse_task(task)
        evidence.extend(task_evidence)
    else:
        verdict = "needs_revision"
        missing_or_risky = ["This POC judge only knows how to evaluate the configured prompt optimization milestones."]

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
