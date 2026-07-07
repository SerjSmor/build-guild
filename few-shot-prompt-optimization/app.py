import json
import urllib.parse
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).parent
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


def status_icon(status):
    return {
        "pending": "○",
        "ready_for_judgment": "◐",
        "needs_revision": "!",
        "complete": "✓"
    }.get(status, "?")


def milestone_status(milestone, progress):
    tasks = milestone["tasks"]
    states = [progress["tasks"].get(task["id"], {}).get("status", "pending") for task in tasks]
    if states and all(state == "complete" for state in states):
        return "complete"
    if any(state in {"ready_for_judgment", "needs_revision", "complete"} for state in states):
        return "in_progress"
    return "pending"


def milestone_prompt(challenge, milestone):
    lines = [
        "Builder role: complete this BuildGuild milestone.",
        "",
        f"Challenge: {challenge['title']}",
        f"Goal: {challenge['goal']}",
    ]

    dataset = challenge.get("dataset")
    if dataset:
        lines.extend([
            "",
            "Dataset:",
            f"- Hugging Face id: {dataset['huggingface_id']}",
            f"- URL: {dataset['url']}",
            "- Load it with:",
            "```python",
            dataset["loading_example"],
            "```"
        ])
        for note in dataset.get("notes", []):
            lines.append(f"- {note}")

    lines.extend([
        "",
        f"Milestone: {milestone['title']}",
        milestone["description"],
        "",
        "Tasks:"
    ])

    for index, task in enumerate(milestone["tasks"], start=1):
        lines.append(f"{index}. {task['title']} (task id: {task['id']})")
        for artifact in task.get("expected_artifacts", []):
            lines.append(f"   - Expected artifact: {artifact}")

    lines.extend([
        "",
        "Expected workflow:",
        "1. Implement the work for the tasks above.",
        "2. Save any required artifacts listed in challenge.json.",
        "3. Update progress by running the appropriate mark_ready.py command.",
        "4. Do not mark tasks complete; the Judge role handles completion."
    ])
    return "\n".join(lines)


def copy_button(text, key):
    payload = json.dumps(text)
    html = f"""
        <button id="copy-{key}" style="
            border: 1px solid #d0d7de;
            border-radius: 6px;
            background: #ffffff;
            color: #24292f;
            cursor: pointer;
            font: 14px sans-serif;
            padding: 0.45rem 0.75rem;
        ">Copy milestone prompt</button>
        <span id="copy-status-{key}" style="
            color: #57606a;
            font: 13px sans-serif;
            margin-left: 0.5rem;
        "></span>
        <script>
        const button = document.getElementById("copy-{key}");
        const status = document.getElementById("copy-status-{key}");
        button.addEventListener("click", async () => {{
            try {{
                await navigator.clipboard.writeText({payload});
                status.textContent = "Copied";
                setTimeout(() => status.textContent = "", 1800);
            }} catch (error) {{
                status.textContent = "Copy failed";
            }}
        }});
        </script>
    """
    src = "data:text/html;charset=utf-8," + urllib.parse.quote(html)
    st.iframe(src, height=42)


def reset_milestone(milestone, progress):
    artifacts = set()
    for task in milestone["tasks"]:
        progress["tasks"][task["id"]] = {
            "status": "pending",
            "builder_notes": "",
            "judge": None
        }
        artifacts.update(task.get("expected_artifacts", []))

    for artifact in artifacts:
        artifact_path = (ROOT / artifact).resolve()
        try:
            artifact_path.relative_to(USER_ARTIFACTS_DIR.resolve())
        except ValueError:
            continue
        if artifact_path.exists() and artifact_path.is_file():
            artifact_path.unlink()

    save_json(PROGRESS_PATH, progress)


def milestone_artifacts(milestone):
    artifacts = []
    seen = set()
    for task in milestone["tasks"]:
        for artifact in task.get("expected_artifacts", []):
            if artifact not in seen:
                artifacts.append(artifact)
                seen.add(artifact)
    return artifacts


def render_artifact_preview(artifact):
    artifact_path = ROOT / artifact
    st.write(f"`{artifact}`")
    if not artifact_path.exists():
        st.info("Missing")
        return

    suffix = artifact_path.suffix.lower()
    try:
        if suffix == ".json":
            st.json(load_json(artifact_path))
        elif suffix in {".py", ".txt", ".md", ".example"}:
            st.code(artifact_path.read_text(encoding="utf-8"), language="python" if suffix == ".py" else "text")
        else:
            st.write(f"{artifact_path.stat().st_size} bytes")
    except Exception as exc:
        st.warning(f"Could not preview artifact: {exc}")


def render_task(task, progress):
    task_state = progress["tasks"].get(task["id"], {"status": "pending", "judge": None})
    with st.expander(f"{status_icon(task_state['status'])} {task['title']}"):
        st.write(f"Status: `{task_state['status']}`")
        st.write(f"Judge level: `{task.get('judge_level', challenge['judging']['default_level'])}`")

        if task.get("expected_artifacts"):
            st.write("Expected artifacts")
            for artifact in task["expected_artifacts"]:
                st.write(f"- `{artifact}`")

        if task_state.get("builder_notes"):
            st.write("Builder notes")
            st.info(task_state["builder_notes"])

        judgment = task_state.get("judge")
        if judgment:
            st.write(f"Verdict: `{judgment['verdict']}`")
            st.write(f"Confidence: `{judgment['confidence']}`")
            st.write("Evidence")
            for item in judgment.get("evidence", []):
                st.write(f"- {item}")
            if judgment.get("missing_or_risky"):
                st.write("Missing or risky")
                for item in judgment["missing_or_risky"]:
                    st.write(f"- {item}")


def render_milestone(milestone, progress):
    state = milestone_status(milestone, progress)
    st.header(f"{status_icon(state)} {milestone['title']}")
    st.write(milestone["description"])

    if st.button("Restart milestone", key=f"restart-{milestone['id']}"):
        reset_milestone(milestone, progress)
        st.rerun()

    prompt = milestone_prompt(challenge, milestone)
    copy_button(prompt, milestone["id"])
    with st.expander("Prompt to paste into coding agent"):
        st.code(prompt, language="text")

    st.subheader("Tasks")
    for task in milestone["tasks"]:
        render_task(task, progress)

    st.subheader("Artifacts")
    artifacts = milestone_artifacts(milestone)
    if not artifacts:
        st.info("No expected artifacts declared for this milestone.")
    for artifact in artifacts:
        with st.expander(artifact, expanded=False):
            render_artifact_preview(artifact)


challenge = load_json(CHALLENGE_PATH)
progress = load_json(PROGRESS_PATH)

st.set_page_config(page_title=challenge["title"], layout="wide")
st.title(challenge["title"])
st.caption(challenge["goal"])

total_tasks = sum(len(milestone["tasks"]) for milestone in challenge["milestones"])
complete_tasks = sum(1 for task in progress["tasks"].values() if task.get("status") == "complete")
st.progress(complete_tasks / total_tasks if total_tasks else 0)
st.write(f"{complete_tasks} of {total_tasks} tasks complete")

tab_labels = [
    f"{status_icon(milestone_status(milestone, progress))} {milestone['title']}"
    for milestone in challenge["milestones"]
]
tabs = st.tabs(tab_labels)

for tab, milestone in zip(tabs, challenge["milestones"]):
    with tab:
        render_milestone(milestone, progress)
