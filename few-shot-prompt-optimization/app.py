import json
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).parent
CHALLENGE_PATH = ROOT / "challenge.json"
PROGRESS_PATH = ROOT / "progress.json"
USER_ARTIFACTS_DIR = ROOT / "user_artifacts"


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg: #10131a;
            --panel: #171b24;
            --panel-soft: #1d2230;
            --border: #343b4f;
            --border-gold: #8a6f35;
            --text: #e8e1d2;
            --muted: #a8a092;
            --gold: #d4af5f;
            --gold-soft: #f0d68a;
            --green: #79b879;
            --red: #c76b6b;
            --blue: #7aa5c8;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(212, 175, 95, 0.10), transparent 30rem),
                linear-gradient(180deg, #11151f 0%, var(--bg) 45%, #0d1016 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        #MainMenu,
        header,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            visibility: hidden;
            height: 0;
        }

        h1, h2, h3 {
            color: var(--text);
            letter-spacing: 0;
        }

        h1 {
            border-bottom: 1px solid rgba(212, 175, 95, 0.45);
            padding-bottom: 0.55rem;
        }

        h2, h3 {
            color: var(--gold-soft);
        }

        p, li, .stMarkdown, .stCaptionContainer {
            color: var(--text);
        }

        .stCaptionContainer {
            color: var(--muted);
        }

        a {
            color: var(--gold-soft) !important;
            text-decoration-color: rgba(212, 175, 95, 0.45) !important;
        }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #8a6f35, #d4af5f);
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 0.25rem;
            border-bottom: 1px solid var(--border);
        }

        [data-testid="stTabs"] [role="tab"] {
            background: var(--panel);
            border: 1px solid var(--border);
            border-bottom: 0;
            border-radius: 6px 6px 0 0;
            color: var(--muted);
            padding: 0.55rem 0.9rem;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            background: linear-gradient(180deg, #24202b, var(--panel-soft));
            border-color: var(--border-gold);
            color: var(--gold-soft);
        }

        [data-testid="stExpander"] {
            background: rgba(23, 27, 36, 0.78);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 0.65rem;
        }

        [data-testid="stExpander"] summary {
            color: var(--text);
            font-weight: 600;
        }

        div[data-testid="stAlert"] {
            background: rgba(29, 34, 48, 0.92);
            border: 1px solid var(--border-gold);
            border-radius: 8px;
            color: var(--text);
        }

        div[data-testid="stCodeBlock"] {
            border: 1px solid var(--border);
            border-radius: 8px;
        }

        code {
            color: var(--gold-soft);
            background: rgba(212, 175, 95, 0.10);
            border-radius: 4px;
            padding: 0.08rem 0.22rem;
        }

        .stTextInput input {
            background: #11151f;
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 6px;
        }

        .stTextInput input:focus {
            border-color: var(--gold);
            box-shadow: 0 0 0 1px rgba(212, 175, 95, 0.25);
        }

        .stButton button {
            background: #171b24;
            border: 1px solid var(--border-gold);
            border-radius: 6px;
            color: var(--gold-soft);
            font-weight: 600;
        }

        .stButton button:hover {
            background: #24202b;
            border-color: var(--gold-soft);
            color: #fff6d6;
        }

        hr {
            border-color: rgba(212, 175, 95, 0.25);
        }

        img {
            border: 1px solid var(--border);
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def milestone_task_counts(milestone, progress):
    total = len(milestone["tasks"])
    complete = sum(
        1
        for task in milestone["tasks"]
        if progress["tasks"].get(task["id"], {}).get("status") == "complete"
    )
    return complete, total


def render_introduction(challenge, progress):
    intro = challenge.get("introduction", {})
    st.header(intro.get("title", "Project Introduction"))

    for paragraph in intro.get("body", []):
        st.markdown(f"- {paragraph}")

    illustration = intro.get("illustration")
    if illustration:
        illustration_path = ROOT / illustration
        if illustration_path.exists():
            st.image(str(illustration_path), use_container_width=True)
        else:
            st.info(f"Add an illustration at `{illustration}` to show it here.")

    st.subheader("Milestones")
    for index, milestone in enumerate(challenge["milestones"], start=1):
        state = milestone_status(milestone, progress)
        complete, total = milestone_task_counts(milestone, progress)
        st.write(f"{index}. {status_icon(state)} **{milestone['title']}** - {complete}/{total} tasks complete")
        st.caption(milestone.get("short_description", milestone.get("description", "")))


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
        milestone.get("long_description", milestone.get("description", "")),
        "",
        "Tasks:"
    ])

    for index, task in enumerate(milestone["tasks"], start=1):
        lines.append(f"{index}. {task['title']} (task id: {task['id']})")
        if task.get("small_hint"):
            lines.append(f"   - Hint: {task['small_hint']}")
        if task.get("full_explanation"):
            lines.append(f"   - Full explanation: {task['full_explanation']}")
        if task.get("bonus"):
            lines.append(f"   - Bonus: {task['bonus']}")
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


def milestone_hint(milestone):
    task_count = len(milestone["tasks"])
    artifact_count = len(milestone_artifacts(milestone))
    return (
        f"Complete the {task_count} tasks in this milestone and save the expected "
        f"{artifact_count} artifact{'s' if artifact_count != 1 else ''} under `user_artifacts/`."
    )


def render_prompt_reveal(challenge, milestone):
    milestone_id = milestone["id"]
    input_key = f"prompt-reveal-input-{milestone_id}"
    visible_key = f"prompt-reveal-visible-{milestone_id}"

    st.info(milestone_hint(milestone))
    reveal = st.text_input(
        f"Type `show me` to reveal the full coding-agent prompt for {milestone['title']}.",
        key=input_key
    )

    if reveal.strip().lower() == "show me":
        st.session_state[visible_key] = True

    if st.session_state.get(visible_key, False):
        prompt = milestone_prompt(challenge, milestone)
        st.code(prompt, language="text")


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

        if task.get("small_hint"):
            st.info(task["small_hint"])

        if task.get("full_explanation"):
            with st.expander("Full explanation"):
                st.write(task["full_explanation"])

        if task.get("bonus"):
            st.success(f"Bonus: {task['bonus']}")

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
    st.write(milestone.get("long_description", milestone.get("description", "")))

    render_prompt_reveal(challenge, milestone)

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

    st.divider()
    if st.button("Restart milestone", key=f"restart-{milestone['id']}"):
        reset_milestone(milestone, progress)
        st.rerun()


challenge = load_json(CHALLENGE_PATH)
progress = load_json(PROGRESS_PATH)

st.set_page_config(page_title=challenge["title"], layout="wide")
apply_theme()
st.title(challenge["title"])
st.caption(challenge["goal"])

total_tasks = sum(len(milestone["tasks"]) for milestone in challenge["milestones"])
complete_tasks = sum(1 for task in progress["tasks"].values() if task.get("status") == "complete")

render_introduction(challenge, progress)

st.divider()
st.header("Workspace")
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
