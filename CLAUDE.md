# CLAUDE.md

Guidance for Claude Code sessions working in this repository.

## Subagent and model use (rule)

Delegate to subagents when it saves time or gives an independent read, and pick the model
by how hard the task is. Pass the tier as the Agent tool's `model` parameter:

| Task | Model tier |
|---|---|
| Quick writing (short docs, commit/PR text, captions) and simple checks (does a file or column exist, did a command pass, are the numbers in a report the same as in its table) | `haiku` |
| Simple coding (small, local edits, tests for existing behaviour, lint/format fixes) and routine checking (re-running and reading test or ruff output, comparing tables against reports) | `sonnet` |
| Complex coding (new analysis modules, statistical or survey-design code, pipeline changes that touch several modules) and the final review before a push or PR | `opus` |

- Do work yourself when it is a few tool calls; delegate only when it pays for itself.
- Run independent subagents in parallel (one message, several Agent calls).
- Give each subagent a self-contained brief: the goal, the files, and what has already been ruled out.
- The final review always gets a fresh-context `opus` agent that sees the code, not your conclusions.

## Project conventions

- Use only the FARS and CRSS data in `data/raw/` (Git LFS). Never modify raw data. Never pool FARS and CRSS rows.
- CRSS inference is design-based (`WEIGHT`, `PSUSTRAT`, `PSU_VAR`). Results are associations conditional on a police-reported crash, not causal effects.
- Never fabricate numbers, in particular drug contributions or enforcement effects. Every number in `reports/` comes from `outputs/tables/` through the templates in `reports/templates/`.
- Do not rewrite validated findings or remove documented limitations (`docs/limitations.md`) to simplify a result.
- Reuse the existing caches and derived datasets; rerun only the module you changed (`uv run nhtsa analyze <module>`) rather than the full ~84-minute `nhtsa all`.
- Generated datasets and caches stay out of Git (`data/interim/`, `data/processed/`, `outputs/cache/`).

## Checks before pushing

```bash
uv run ruff check src tests app
uv run ruff format --check src tests app
uv run pytest -q
```

CI runs the same checks without the data; tests that need the Parquet caches skip themselves.
