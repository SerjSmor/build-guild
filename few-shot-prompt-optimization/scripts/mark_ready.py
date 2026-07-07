#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_PATH = ROOT / "challenge.json"
PROGRESS_PATH = ROOT / "progress.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def task_ids_for_milestone(challenge, milestone_id):
    for milestone in challenge["milestones"]:
        if milestone["id"] == milestone_id:
            return [task["id"] for task in milestone["tasks"]]
    raise SystemExit(f"Unknown milestone id: {milestone_id}")


def main():
    parser = argparse.ArgumentParser(description="Mark a task ready for judge review.")
    parser.add_argument("task_id", nargs="?", help="Task id to mark ready.")
    parser.add_argument("--all", action="store_true", help="Mark all tasks ready.")
    parser.add_argument("--milestone", help="Mark every task in one milestone ready.")
    parser.add_argument("--notes", default="", help="Builder notes for the judge.")
    args = parser.parse_args()

    challenge = load_json(CHALLENGE_PATH)
    progress = load_json(PROGRESS_PATH)

    if sum(bool(value) for value in [args.all, args.milestone, args.task_id]) != 1:
        raise SystemExit("Pass exactly one of: task id, --milestone, or --all.")

    if args.all:
        task_ids = list(progress["tasks"])
    elif args.milestone:
        task_ids = task_ids_for_milestone(challenge, args.milestone)
    elif args.task_id:
        task_ids = [args.task_id]

    unknown = [task_id for task_id in task_ids if task_id not in progress["tasks"]]
    if unknown:
        raise SystemExit(f"Unknown task id: {', '.join(unknown)}")

    for task_id in task_ids:
        task = progress["tasks"][task_id]
        task["status"] = "ready_for_judgment"
        task["builder_notes"] = args.notes
        task["judge"] = None
        task["ready_at"] = datetime.now(timezone.utc).isoformat()

    save_json(PROGRESS_PATH, progress)
    if args.all:
        print(f"{len(task_ids)} tasks: ready_for_judgment")
        return
    if args.milestone:
        print(f"{args.milestone}: {len(task_ids)} tasks ready_for_judgment")
        return

    if args.task_id not in progress["tasks"]:
        raise SystemExit(f"Unknown task id: {args.task_id}")
    print(f"{args.task_id}: ready_for_judgment")


if __name__ == "__main__":
    main()
