# CI Failure Diagnostic Agent

An autonomous AI agent that analyzes CI/CD log files, identifies the root cause of failures, and returns a structured diagnostic report — all in a single command.

---

## Overview

The CI Failure Diagnostic Agent is a LangGraph-powered ReAct agent backed by Google's Gemini 2.5 Flash model. Given a raw CI log file, the agent orchestrates a deterministic three-step pipeline: it parses the log for error details, classifies the failure category, and suggests an actionable fix. The final output is a clean JSON report ready for consumption by humans or downstream automation.

---

## Project Structure

```
ci-diagnostic-agent/
├── agent.py        # Agent definition and run logic
├── main.py         # CLI entrypoint
├── tools.py        # LangChain tools (parse, classify, suggest)
├── requirements.txt
└── README.md
```

---

## How It Works

The agent follows a strict, sequential three-step reasoning loop using the ReAct (Reason + Act) pattern:

```
CI Log Input
     │
     ▼
┌─────────────────────┐
│  1. parse_log_tool  │  ── Extracts error_type, file_name, line_number via regex
└─────────────────────┘
     │
     ▼
┌──────────────────────────┐
│  2. classify_failure_tool│  ── Maps error_type → failure category
└──────────────────────────┘
     │
     ▼
┌────────────────────────┐
│  3. suggest_fix_tool   │  ── Returns a human-readable fix suggestion
└────────────────────────┘
     │
     ▼
JSON Diagnostic Report
```

The system prompt instructs the agent to call these tools in order and to format its final answer as a raw JSON object with four keys: `error_type`, `location`, `category`, and `suggested_fix`.

---

## Components

### `agent.py`

Contains two functions:

**`create_agent()`** — Initialises the Gemini 2.5 Flash LLM with `temperature=0.0` for deterministic outputs, registers the three tools, and builds a LangGraph ReAct agent with a strict system prompt.

**`run_diagnostic(log_content: str) -> dict`** — Invokes the agent with the raw log string, extracts the final message from the LangGraph state, strips any stray markdown fencing the LLM may add, and parses the result into a Python dictionary. Returns `{"error": "...", "raw_response": "..."}` on parse failure.

---

### `main.py`

A minimal CLI wrapper. Accepts a `--log` argument pointing to a log file, reads it, calls `run_diagnostic`, and pretty-prints the resulting JSON report.

```
usage: main.py --log <path-to-log-file>
```

---

### `tools.py`

Three `@tool`-decorated LangChain functions:

**`parse_log_tool(log_content: str) -> dict`**

Applies two regex patterns to the raw log string:
- Scans for the pattern `E   <ErrorName>:` to extract the `error_type`.
- Uses `findall` with a `file:line` pattern across all lines, then takes the **last** match as the root-cause location (the deepest frame in the traceback).

Returns `{ "error_type": "...", "file_name": "...", "line_number": "..." }`.

**`classify_failure_tool(error_type: str) -> str`**

Performs keyword matching on the lowercased error type string to map it to one of four categories:

| Keyword match | Category |
|---|---|
| `module` or `import` | `dependency error` |
| `timeout` | `timeout` |
| `syntax` or `indentation` | `build error` |
| anything else | `test failure` |

**`suggest_fix_tool(error_type: str, category: str) -> str`**

Returns a fix string based on exact `error_type` match first, then falls back to `category`:

| Condition | Suggested fix |
|---|---|
| `ZeroDivisionError` | Guard denominator with a conditional check |
| `dependency error` | Verify module is in `requirements.txt` and installed |
| `build error` | Review syntax around the failing line |
| default | Review assertion inputs and handle edge cases |

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/your-username/ci-diagnostic-agent.git
cd ci-diagnostic-agent
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

Minimum required packages:

```
langchain-google-genai
langgraph
langchain-core
```

**4. Set your Google API key**

The agent uses the Gemini API via `langchain-google-genai`. Export your key before running:

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

On Windows:

```bash
set GOOGLE_API_KEY=your-api-key-here
```

---

## Usage

```bash
python main.py --log path/to/your/ci_log.txt
```

**Example output:**

```
Analyzing log...

--- Diagnostic Report ---
{
    "error_type": "ZeroDivisionError",
    "location": "tests/test_math.py:42",
    "category": "test failure",
    "suggested_fix": "Add a conditional check to ensure the denominator is not zero before dividing."
}
```

---

## Example CI Log

The following is a minimal log that the agent can successfully process:

```
FAILED tests/test_math.py::test_divide - ZeroDivisionError: division by zero

  File "src/math_utils.py", line 15, in divide
    return a / b
E       ZeroDivisionError: division by zero

tests/test_math.py:42: ZeroDivisionError
```

---

## Error Handling

If the agent fails to produce valid JSON (e.g., the LLM returns an unexpected format), `run_diagnostic` returns a fallback dictionary:

```json
{
    "error": "Failed to parse JSON",
    "raw_response": "<whatever the LLM returned>"
}
```

The function also handles the case where Gemini returns a list of content blocks instead of a plain string, joining them safely before parsing.

---

## Design Decisions

**Why LangGraph over a custom loop?**
LangGraph's `create_react_agent` provides a production-grade ReAct loop with built-in state management, tool invocation retries, and message history — replacing custom `AgentExecutor` boilerplate with a single function call.

**Why `temperature=0.0`?**
CI diagnostics are deterministic by nature. Zero temperature minimises variation in tool call order and JSON formatting, making the agent's output reliable across repeated runs on the same log.

**Why take the last `file:line` match in `parse_log_tool`?**
Python tracebacks list frames from outermost call to innermost. The last match is the deepest frame — the actual line that raised the exception — which is the most actionable location for a developer.

**Why strip markdown fencing in `run_diagnostic`?**
Even with explicit instructions to return raw JSON, LLMs occasionally wrap output in ` ```json ``` ` blocks. The stripping logic is a defensive measure that keeps the output contract clean without relying solely on prompt adherence.

---

## Extending the Agent

**Adding new error categories** — extend the `if/elif` chain in `classify_failure_tool` with additional keyword patterns.

**Adding new fix suggestions** — add `if` branches to `suggest_fix_tool` keyed on specific error types or categories.

**Supporting more log formats** — update the regex patterns in `parse_log_tool`. The current patterns target pytest-style tracebacks; adapting to Maven, Gradle, or GitHub Actions logs requires adding alternative regex branches.

**Switching the LLM** — replace `ChatGoogleGenerativeAI` in `create_agent()` with any LangChain-compatible chat model (e.g., `ChatOpenAI`, `ChatAnthropic`). The rest of the agent is model-agnostic.

---
