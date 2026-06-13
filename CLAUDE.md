# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A small LangGraph-based agent that diagnoses CI failures from raw log text. It parses a pytest-style traceback, classifies the failure category, and suggests a fix — returning the result as a JSON report.

## Commands

```bash
# Install dependencies (venv/ already exists in this repo)
pip install -r requirements.txt

# Run the agent against a log file
python main.py --log sample_logs/sample_failure.log

# Run all tests
pytest

# Run a single test
pytest tests/test_agent.py::test_parse_log_tool

# Write the JSON report to a file in addition to stdout
python main.py --log sample_logs/sample_failure.log --output diagnostic_report.json

# Install dev dependencies (lint/type-check tools)
pip install -r requirements-dev.txt

# Lint and type-check
ruff check .
mypy main.py agent.py tools.py tests/
```

The agent requires a `GOOGLE_API_KEY` environment variable (used by `ChatGoogleGenerativeAI` / Gemini 2.5 Flash) to run `main.py`. The unit tests in `tests/test_agent.py` only exercise `tools.py` directly and do not call the LLM, so they run without an API key.

## Architecture

- **main.py** — CLI entry point. Reads a log file passed via `--log`, calls `run_diagnostic`, and prints the resulting JSON report.
- **agent.py** — Builds a LangGraph `create_react_agent` (Gemini 2.5 Flash, temperature 0) wired to the three tools in `tools.py`. The system prompt forces the agent to call the tools in a fixed sequence (`parse_log_tool` → `classify_failure_tool` → `suggest_fix_tool`) and to return its final answer as a raw JSON object with keys `error_type`, `location`, `category`, `suggested_fix`. `run_diagnostic(log_content)` invokes the agent, extracts the final message content (handling both plain-string and block-list response shapes), strips any ```json fences, and `json.loads`s the result — returning `{"error": "Failed to parse JSON", "raw_response": ...}` if parsing fails.
- **tools.py** — Three `@tool`-decorated functions, all pure/regex-based (no LLM calls):
  - `parse_log_tool`: regex-extracts the error type (`E   <Name>Error:`) and the **last** `file:line` match in the log (the deepest frame / root cause).
  - `classify_failure_tool`: maps an error type string to a category (`dependency error`, `timeout`, `build error`, or `test failure`) via keyword matching.
  - `suggest_fix_tool`: returns a canned remediation string based on `error_type`/`category`, with a special case for `ZeroDivisionError`.

Because the agent's behavior depends on an LLM following a fixed tool-call sequence and a strict output format, most logic worth testing deterministically lives in `tools.py` — prefer adding/extending tests there over mocking the agent.

## Linting and type-checking

`pyproject.toml` configures both tools (versions pinned in `requirements-dev.txt`):

- **ruff** — `select = ["E4", "E7", "E9", "F", "I"]` (pyflakes errors + import sorting), `exclude = ["venv"]`.
- **mypy** — `ignore_missing_imports = true` (langchain/langgraph have incomplete type stubs), `exclude = ["venv"]`. Run against `main.py agent.py tools.py tests/` explicitly rather than `.` to avoid scanning `venv/`.

## CI / GitHub Actions integration

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs on every `pull_request` and on `push` to `main`, with two jobs:

- **lint** — installs `requirements-dev.txt` and runs `ruff check .` and `mypy main.py agent.py tools.py tests/`.
- **test**:
  1. Installs dependencies and runs `pytest`, capturing combined output to `pytest_output.log` (the step is allowed to fail without aborting the job).
  2. If `pytest` failed, runs `python main.py --log pytest_output.log --output diagnostic_report.json` to generate a diagnostic report. This step requires a `GOOGLE_API_KEY` repository secret to be configured (Settings → Secrets and variables → Actions).
  3. Posts the report as a comment on the PR (`issues.createComment`) for `pull_request` events, or as a commit comment (`repos.createCommitComment`) for `push` events.
  4. Re-fails the job if `pytest` failed, so the workflow's overall status still reflects the real test result.