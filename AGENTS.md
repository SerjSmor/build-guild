# BuildGuild Agent Roles

This repo contains AI engineering quests. Each quest lives in its own subfolder and is designed to be completed by a coding agent.

The coding agent has two separate roles:

## Builder Role

Use this role when implementing a task.

- Read the quest's `challenge.json`.
- Pick one pending task.
- Build the requested artifact.
- Store learner-created files under the quest's `user_artifacts/` directory unless the quest says otherwise.
- Update `progress.json` with notes and set the task status to `ready_for_judgment`.
- Do not mark your own work as `complete`.

## Judge Role

Use this role when evaluating a task.

- Read the quest's `challenge.json`, `progress.json`, and relevant artifacts.
- Do not implement fixes while judging.
- Judge each task independently.
- Use the task's `judge_level`:
  - `easy`: check plausible evidence and expected artifacts.
  - `medium`: inspect implementation and run available checks.
  - `hard`: perform strict behavioral review and look for superficial implementations.
- Write a verdict with evidence.
- Only the judge may mark a task `complete`.

Milestone status is derived from task status. A milestone is complete only when all required tasks are complete.

Restart actions may delete files inside a quest's `user_artifacts/` directory. Do not store reusable templates, source code, or cross-quest outputs there.
