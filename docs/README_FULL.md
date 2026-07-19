# 📋 Meeting Notes → Action Items Extractor

> A **multi-agent pipeline** that converts raw meeting transcripts into a structured, prioritized, deduplicated task list — fully deterministic, observable, and comparable against a single-agent baseline.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Quick Start](#2-quick-start)
3. [Project Structure](#3-project-structure)
4. [Architecture](#4-architecture)
   - [Multi-Agent Pipeline](#multi-agent-pipeline)
   - [State Machine](#state-machine)
   - [Agent Roles & Tools](#agent-roles--tools)
5. [Source Module Reference](#5-source-module-reference)
   - [schemas.py](#schemspy--data-models)
   - [tools.py](#toolspy--tool-functions)
   - [agents.py](#agentspy--agent-implementations)
   - [orchestrator.py](#orchestratorpy--pipeline-runner)
   - [state_machine.py](#state_machinepy--state-machine)
   - [guardrails.py](#guardrailspy--safety-layer)
   - [logging_utils.py](#logging_utilspy--observability)
   - [evaluation.py](#evaluationpy--evaluation-harness)
   - [scenarios.py](#scenariospy--test-scenarios)
   - [analysis.py](#analysispy--meeting-summarizer)
   - [baseline_single_agent.py](#baseline_single_agentpy--baseline)
6. [Streamlit UI (app.py)](#6-streamlit-ui-apppy)
7. [Data Models](#7-data-models)
8. [Guardrails & Safety](#8-guardrails--safety)
9. [Observability & Logging](#9-observability--logging)
10. [Evaluation & Metrics](#10-evaluation--metrics)
11. [Reproducibility](#11-reproducibility)
12. [Environment Variables](#12-environment-variables)
13. [Running the CLI Evaluation](#13-running-the-cli-evaluation)
14. [Demo Script (5–7 min)](#14-demo-script-57-min)
15. [Team & Contribution](#15-team--contribution)

---

## 1. Project Overview

**Meeting Notes → Action Items Extractor** is a Python application that takes a raw, conversational meeting transcript and produces a structured, prioritized task list with:

- **Owners** — who is responsible (via `@mention`, first-person commitment, "Name will ..." patterns)
- **Deadlines** — parsed from natural language ("by Friday", "within 48 hours", "tomorrow at 2 PM")
- **Categories** — Engineering, Product, Marketing, Sales, Operations, Customer Success, Leadership, Other
- **Priority** — P1 / P2 / P3 based on urgency, deadline proximity, and keyword signals
- **Confidence scores** — how certain the system is that a sentence is truly an action item (0–1)

The system uses **four specialized agents** orchestrated through an **explicit state machine**, with full **JSONL observability**, **Pydantic schema validation**, **guardrails**, and a **baseline single-agent** comparison for metrics.

### Key Design Goals

| Goal | Implementation |
|------|----------------|
| Deterministic / reproducible | Seed-based `ToolContext`; regex tools (no LLM randomness) |
| Observable | Every event logged to JSONL per run |
| Safe | Tool allowlist, output validation, step budget, timeout |
| Comparable | Parallel baseline agent run for metric comparison |
| Extensible | Agents and tools are decoupled; schemas enforce contracts |

---

## 2. Quick Start

### Prerequisites

- Python 3.10+
- Windows / Linux / macOS

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd meeting-notes-to-action-item-extractor

# 2. Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment (optional – no API key needed for local runs)
copy .env.example .env
```

### Run the Streamlit App

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

### Run the CLI Evaluation

```bash
python -m src
```

This runs reproducibility checks + 10-scenario evaluation and prints a summary table.

---

## 3. Project Structure

```
meeting-notes-to-action-item-extractor/
│
├── app.py                        # Streamlit UI — 7 tabs
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .gitignore
├── LICENSE
│
├── src/                          # Core library
│   ├── __init__.py
│   ├── __main__.py               # CLI entry point (reproducibility + eval)
│   ├── schemas.py                # Pydantic models for all data types
│   ├── tools.py                  # All tool functions (deterministic, seedable)
│   ├── agents.py                 # Agent implementations (Parser, Classifier, Prioritizer, Baseline, Summary)
│   ├── orchestrator.py           # Pipeline runner + RunOutput
│   ├── state_machine.py          # Explicit state machine with transition logging
│   ├── guardrails.py             # Tool allowlist, output validation, timeout
│   ├── logging_utils.py          # JSONL logger + run replay
│   ├── evaluation.py             # 10-scenario evaluation harness, 5 metrics
│   ├── scenarios.py              # 8–10 built-in test scenarios
│   ├── analysis.py               # Meeting summarizer (decisions, key topics, ...)
│   └── baseline_single_agent.py  # Reference single-agent implementation
│
├── docs/                         # Documentation
│   ├── architecture.md           # System design + agent roles + tool schemas
│   ├── agent_interaction_diagram.md  # Mermaid sequence diagram
│   └── evaluation_report.md      # Per-scenario metrics results
│
├── evaluation/
│   └── test_scenarios.json       # JSON test scenario definitions
│
└── runs/                         # Auto-created: JSONL logs + summary JSONs
    ├── <run_id>.jsonl
    └── <run_id>.summary.json
```

---

## 4. Architecture

### Multi-Agent Pipeline

```
User / Streamlit UI
        │
        ▼
  ┌───────────────────────────────────────────────────────────────┐
  │                        Orchestrator                           │
  │                                                               │
  │   StateMachine: IDLE → TRANSCRIPT_RECEIVED → PARSING          │
  │            → TASKS_EXTRACTED → CLASSIFYING → PRIORITIZING     │
  │            → SUMMARIZING → COMPLETED → DONE                   │
  │            Any state → ERROR | STOPPED                        │
  │                                                               │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐  │
  │  │ TranscriptParser │→ │  TaskClassifier  │→ │  Priority  │  │
  │  │     Agent        │  │     Agent        │  │   Agent    │  │
  │  └──────────────────┘  └──────────────────┘  └────────────┘  │
  │         │                      │                   │          │
  │ [transcript_parse]       [task_classify]    [priority_score]  │
  │ [extract_action_items]   [deduplicate]                        │
  │                                                               │
  │  ┌──────────────────┐   ┌──────────────────────────────────┐  │
  │  │  SummaryAgent    │   │  BaselineAgent (single-pass)    │  │
  │  │ [meeting_summ.]  │   │  (no separation, no dedup)       │  │
  │  └──────────────────┘   └──────────────────────────────────┘  │
  └───────────────────────────────────────────────────────────────┘
        │
        ▼
  JSONL log (runs/<run_id>.jsonl)
  Summary JSON (runs/<run_id>.summary.json)
  Streamlit UI (7 tabs)
```

### State Machine

| From State | Event | To State |
|-----------|-------|---------|
| `IDLE` | `receive_transcript` | `TRANSCRIPT_RECEIVED` |
| `TRANSCRIPT_RECEIVED` | `start_parse` | `PARSING` |
| `PARSING` | `tasks_extracted` | `TASKS_EXTRACTED` |
| `TASKS_EXTRACTED` | `start_classify` | `CLASSIFYING` |
| `CLASSIFYING` | `start_prioritize` | `PRIORITIZING` |
| `PRIORITIZING` | `start_summarize` | `SUMMARIZING` |
| `SUMMARIZING` | `summarized` | `COMPLETED` |
| `COMPLETED` | `done` | `DONE` |
| Any | `stop` | `STOPPED` |
| Any | `error` | `ERROR` |

The state machine enforces a **step budget** (`max_steps`, default `20`). If exceeded, it raises `RuntimeError` and transitions to `ERROR`.

### Agent Roles & Tools

| Agent | State | Tools Used | Input → Output |
|-------|-------|-----------|----------------|
| **TranscriptParserAgent** | `PARSING` | `transcript_parse`, `extract_action_items` | `raw_text` → `list[ActionItem]` with confidence scores |
| **TaskClassifierAgent** | `CLASSIFYING` | `task_classify`, `deduplicate` | `list[ActionItem]` → enriched, deduplicated `list[ActionItem]` |
| **PriorityAgent** | `PRIORITIZING` | `priority_score` | `list[ActionItem]` → sorted `list[ActionItem]` with P1/P2/P3 labels |
| **SummaryAgent** | `SUMMARIZING` | `meeting_summarize` | `raw_text` + `list[ActionItem]` → `dict` analysis |
| **BaselineAgent** | (post-DONE) | all 4 tools combined | `raw_text` → `list[ActionItem]` (for metric comparison) |

---

## 5. Source Module Reference

### `schemas.py` — Data Models

All inter-agent data is typed and validated using **Pydantic v2** models.

#### Core Models

```python
class ActionItem(BaseModel):
    id: str                        # Unique task ID (e.g., "T001")
    title: str                     # Cleaned task description
    owner: str                     # Assigned owner (default "Unassigned")
    deadline: str | None           # ISO date / datetime string or "ASAP"
    deadline_parse_method: str | None  # How the deadline was inferred
    category: Literal[             # Task department category
        "Engineering", "Product", "Marketing",
        "Sales", "Operations", "Customer Success",
        "Leadership", "Other"
    ]
    priority_score: int            # 1–10 urgency score
    priority_label: Literal["P1", "P2", "P3"]
    dependencies: list[str]        # IDs of blocking tasks
    status: Literal["Pending", "In Progress", "Done"]
    source_speakers: list[str]     # Speakers who mentioned this item
    confidence_score: float        # 0.0–1.0 action-item likelihood
    priority_rule_hits: list[str]  # Which scoring rules fired
```

#### Enums

```python
class SystemState(str, Enum):
    IDLE, TRANSCRIPT_RECEIVED, PARSING, TASKS_EXTRACTED,
    CLASSIFYING, PRIORITIZING, SUMMARIZING, COMPLETED, DONE,
    ERROR, STOPPED

class ToolName(str, Enum):
    TRANSCRIPT_PARSE, EXTRACT_ACTION_ITEMS, TASK_CLASSIFY,
    PRIORITY_SCORE, DEDUPLICATE, MEETING_SUMMARIZE

class LogEventType(str, Enum):
    RUN_START, RUN_END, STATE_TRANSITION, AGENT_INVOKE,
    TOOL_CALL, TOOL_RESULT, MESSAGE, METRICS, ERROR, GUARDRAIL
```

#### Agent I/O Models

| Input | Output |
|-------|--------|
| `TranscriptParserInput(raw_text)` | `TranscriptParserOutput(transcript, items)` |
| `TaskClassifierInput(items)` | `TaskClassifierOutput(items)` |
| `PriorityAgentInput(items)` | `PriorityAgentOutput(items)` |
| `SummaryAgentInput(raw_text, items)` | `SummaryAgentOutput(analysis)` |
| `BaselineAgentInput(raw_text)` | `BaselineAgentOutput(items)` |

---

### `tools.py` — Tool Functions

All tool functions are **deterministic** (regex-based, no LLM) and accept a `ToolContext(seed, meeting_date)`.

#### `ToolContext`

```python
@dataclass
class ToolContext:
    seed: int
    meeting_date: date  # Anchors relative deadline calculations
```

#### `transcript_parse(raw_text, ctx) → Transcript`

- Splits lines with pattern `Speaker: text`
- Groups consecutive lines under the same speaker into one `TranscriptTurn`
- Returns `Transcript(raw_text, turns: list[TranscriptTurn])`

#### `extract_action_items(transcript, ctx) → list[ActionItem]`

Scans each turn sentence by sentence:

| Pattern Type | Confidence | Examples |
|---|---|---|
| Explicit keyword (`action item`, `please`, `can you`, `let's`) | `0.9` | "Action item: send the deck" |
| First-person commitment (`I'll`, `we will`, `I can`) | `0.65` | "I'll draft the report by tomorrow" |
| Imperative with deadline verb | `0.85` | "Finalize the design by Friday" |
| `must` / `needs to` | `0.65` | "Bob must review the build" |
| `will ... by` pattern | `0.65` | "Taylor will send slides by EOD" |

Filters out opinions and commentary (`"I think..."`, budget-conditional phrases).

#### `task_classify(items, ctx) → list[ActionItem]`

For each item:

**Owner detection** (priority order):
1. Explicit first-person (`I'll`, `We'll`, `Let me`) → speaker
2. `@mention` → mentioned name
3. `"Name will/can/should verb"` pattern → name
4. `"Name please verb"` / `"Name, verb"` pattern → name
5. `"We need to"` → `"Team"`
6. Imperative with deadline and no assignment → speaker (summary-section heuristic)
7. Default → `"Unassigned"`

**Deadline detection** (priority order):
1. `ASAP` / `as soon as possible` → `"ASAP"`
2. `within N weeks` / `within two weeks` → computed date
3. `within N hours` → computed datetime
4. `tonight [HH PM]` → same-day datetime
5. `tomorrow [at HH PM]` → next-day date/datetime
6. `by <weekday/date>` → next matching weekday or parsed date
7. `before <date>` / `starting <date>` → parsed date
8. `today` / `EOD` → meeting date
9. `around <date>` → approximate parsed date
10. Fuzzy date anywhere in sentence → `dateutil.parser.parse`

**Category classification** (first regex rule match):
| Rule Pattern | Category |
|---|---|
| `api, backend, deploy, build, ios, android...` | Engineering |
| `feature, product, design, mockups, requirements...` | Product |
| `launch, email, campaign, social, landing page...` | Marketing |
| `pricing, sales, deck, clients, investors...` | Sales |
| `documentation, training, checklists, coordination...` | Operations |
| `support, customer, faq, training material...` | Customer Success |
| `approve, review, freeze, risk, critical...` | Leadership |
| _(no match)_ | Other |

#### `deduplicate(items) → list[ActionItem]`

Two-pass deduplication:

1. **Exact-key** deduplication: `(owner.lower(), deadline.lower(), normalized_title.lower())`
2. **Fuzzy deduplication** — removes items where:
   - Same owner + deadline + **≥75% word-level Jaccard overlap** on title, OR
   - **≥80% containment** (substring heuristic) on title, OR
   - **≥50% word overlap** regardless of owner (cross-speaker duplicates)
3. Items with fewer than 3 words in the title are dropped.

#### `priority_score(items, ctx) → list[ActionItem]`

Scores each item from 1–10:

| Rule | Score Bonus | Trigger |
|------|-------------|---------|
| Strategic launch keywords | +3 | `launch`, `release`, `q2`, `may 15`, `public launch` |
| External pressure | +2 | `investors`, `traction`, `review`, `cannot happen` |
| Deadline within 7 days | +3 | parsed deadline ≤ 7 days from meeting date |
| Deadline within 8–14 days | +2 | parsed deadline 8–14 days out |
| Deadline within 15–30 days | +1 | parsed deadline 15–30 days out |
| Urgency keywords | +2 | `critical`, `urgent`, `asap`, `no delays`, `mitigate` |
| Risk / blocking keywords | +2 | `risk`, `scope creep`, `freeze`, `blocked`, `delay` |
| Dependency signals | +1 | `approval`, `depends`, `waiting`, `need final` |
| External stakeholders | +1 | `legal`, `enterprise`, `apple`, `clients` |
| High confidence (≥0.85) | +1 | confidence_score ≥ 0.85 |

Labels: **P1** (score ≥ 8), **P2** (score ≥ 5), **P3** (score < 5). Output sorted descending by score.

#### `meeting_summarize(raw_text, items, ctx) → dict`

Delegates to `analysis.generate_analysis(...)`. Returns a dict with:
- `meeting_summary` — 2–3 sentence summary
- `decisions_made` — list of key decisions
- `key_topics` — list of discussed topics
- `participants` — extracted speaker names
- `next_steps` — high-level next steps

---

### `agents.py` — Agent Implementations

Each agent is a `@dataclass` with a single `.run(input_model, ctx, logger)` method.

#### `TranscriptParserAgent`

1. Logs invocation (with SHA-256 hash of raw text for traceability)
2. Calls `transcript_parse(raw_text, ctx)` → `Transcript`
3. Calls `extract_action_items(transcript, ctx)` → `list[ActionItem]`
4. Validates output via Pydantic, logs result
5. Returns `TranscriptParserOutput`

#### `TaskClassifierAgent`

1. Calls `task_classify(items, ctx)` → classified items
2. Calls `deduplicate(classified)` → deduped items
3. Validates, logs, returns `TaskClassifierOutput`

#### `PriorityAgent`

1. Calls `priority_score(items, ctx)` → sorted, scored items
2. Logs rule hits per item, validates, returns `PriorityAgentOutput`

#### `SummaryAgent`

1. Calls `meeting_summarize(raw_text, items, ctx)` → analysis dict
2. Logs summary length + decisions count, returns `SummaryAgentOutput`

#### `BaselineAgent`

Single-pass: runs all 4 tools in sequence with **no deduplication and no role separation** — used purely for metric comparison.

---

### `orchestrator.py` — Pipeline Runner

#### `RunConfig`

```python
@dataclass
class RunConfig:
    seed: int                    # RNG seed for reproducibility
    meeting_date: date           # Anchors relative date parsing
    max_steps: int = 20          # State machine step budget
    run_dir: str = "runs"        # Where JSONL logs are saved
```

#### `RunOutput`

```python
@dataclass
class RunOutput:
    run_id: str                  # 12-char hex UUID
    items: list[ActionItem]      # Final prioritized items
    baseline_items: list[Any]    # Baseline agent items (for comparison)
    state_machine: StateMachine  # Full state machine with transitions
    metrics: dict[str, Any]      # Computed metrics dict
    output_json: dict[str, Any]  # JSON-serializable task list
    agent_messages: list[dict]   # Human-readable agent messages
    active_agent: str            # Last active agent name
    analysis: dict[str, Any]     # SummaryAgent output
```

#### `run_pipeline(raw_text, cfg, stop_flag=None) → RunOutput`

Full pipeline execution:

```
1. Initialize RunLogger + StateMachine
2. IDLE → TRANSCRIPT_RECEIVED
3. [check stop_flag]
4. TRANSCRIPT_RECEIVED → PARSING → run TranscriptParserAgent
5. PARSING → TASKS_EXTRACTED
6. [check stop_flag]
7. TASKS_EXTRACTED → CLASSIFYING → run TaskClassifierAgent
8. [check stop_flag]
9. CLASSIFYING → PRIORITIZING → run PriorityAgent
10. PRIORITIZING → SUMMARIZING → run SummaryAgent
11. SUMMARIZING → COMPLETED → run BaselineAgent (for comparison)
12. COMPLETED → DONE
13. Compute metrics, write logs, return RunOutput
```

On any exception: transition → `ERROR`, log error, return empty `RunOutput`.

#### Computed Metrics

| Metric | Formula |
|--------|---------|
| `items_count` | total items extracted |
| `owner_rate` | items with owner ≠ "Unassigned" / total |
| `deadline_rate` | items with deadline / total |
| `p1_count`, `p1_rate` | P1 items / total |
| `mean_confidence_score` | average confidence |
| `baseline_items_count` | baseline agent item count |
| `same_count_as_baseline` | 1 if counts match |
| `processing_time_ms` | wall-clock ms |

---

### `state_machine.py` — State Machine

```python
@dataclass
class StateMachine:
    state: SystemState            # Current state
    transitions: list[StateTransition]  # Full history
    seed: int                     # For seeded RNG
    max_steps: int = 50           # Step budget
    steps: int = 0                # Steps taken so far
    last_error: str | None        # Last error message
    rng: random.Random            # Seeded RNG instance
```

**Methods:**

- `transition(event, next_state) → StateTransition` — Advance state; raises if in `ERROR` or budget exceeded
- `error(event, error, details) → StateTransition` — Transition to `ERROR`

---

### `guardrails.py` — Safety Layer

Three guardrail mechanisms:

#### 1. Tool Allowlist

```python
ALLOWED_TOOLS = {
    "transcript_parse", "extract_action_items",
    "task_classify", "priority_score",
    "deduplicate", "meeting_summarize"
}
```

`validate_tool_call(tool_name)` raises `ValueError` if the tool is not in `ALLOWED_TOOLS`. Called at the start of **every** tool function.

#### 2. Output Schema Validation

`validate_output(items) → list[ActionItem]`: validates every item in a list against the `ActionItem` Pydantic model. Raises `ValueError` on schema mismatch.

#### 3. Timeout Guard

```python
with TimeoutGuard(seconds=10, tool_name="transcript_parse"):
    result = slow_tool(...)
```

Background daemon thread timer. Marks `_timed_out` flag; raises `ToolTimeoutError` on `__exit__` if fired.

#### 4. Step Budget

`StateMachine.max_steps` (default 20) — prevents infinite loops.

#### 5. Human Override (Stop Button)

`stop_flag["stop"] = True` — checked after each agent step; transitions to `STOPPED` gracefully.

---

### `logging_utils.py` — Observability

#### `RunLogger`

```python
@dataclass
class RunLogger:
    run_id: str
    run_dir: str   # e.g., "runs"

    # Core API
    def log(type_: LogEventType, payload: dict) -> None
    def write_summary(summary: dict) -> None

    # Convenience helpers (structured payloads)
    def log_agent_invoke(agent, input_payload)
    def log_agent_result(agent, output_payload)
    def log_tool_call(tool, input_payload)
    def log_tool_result(tool, output_payload)
    def log_state_transition(prev, event, next_state)
    def log_metrics(metrics)
    def log_error(error, details=None)
```

Each call appends a JSON line to `runs/<run_id>.jsonl`:

```json
{
  "run_id": "a3f9bc12e4d7",
  "ts": "2026-02-27T17:45:23.412Z",
  "type": "tool_call",
  "payload": {"tool": "task_classify", "input": {"count": 3}}
}
```

#### `replay_run(run_dir, run_id) → list[LogEvent]`

Reads and parses a JSONL file in order → list of `LogEvent` objects (for the UI's **Logs** tab).

---

### `evaluation.py` — Evaluation Harness

#### `run_evaluation(seed=7) → EvalResult`

Runs all scenarios from `src/scenarios.py` through `run_pipeline`, computes 5 metrics per scenario, aggregates means.

```python
@dataclass
class EvalResult:
    scenarios: int
    scenario_results: list[EvalScenarioResult]
    mean_title_jaccard_vs_baseline: float
    mean_owner_rate: float
    mean_deadline_rate: float
    mean_p1_rate: float
    mean_confidence: float
```

#### Metric Definitions

| # | Metric | Definition |
|---|--------|-----------|
| 1 | **Owner Rate** | Fraction of items with owner ≠ "Unassigned" |
| 2 | **Deadline Rate** | Fraction of items with a parsed deadline |
| 3 | **P1 Rate** | Fraction of items labeled P1 |
| 4 | **Mean Confidence** | Average `confidence_score` across all items |
| 5 | **Jaccard vs Baseline** | Word-level Jaccard of title sets: multi-agent vs. baseline |

Jaccard: `|A ∩ B| / |A ∪ B|` on normalized, lowercased titles.

---

### `scenarios.py` — Test Scenarios

`SCENARIOS: dict[str, str]` — built-in transcript strings keyed by scenario name.

| Scenario Key | Description |
|---|---|
| `scenario_01_basic` | Simple Q&A transcript (capital cities, population) |
| `scenario_02_bug` | Bug report with support steps |
| `scenario_03_research` | Research query with information delivery |
| `scenario_04_admin` | Admin permission management |
| `scenario_05_deliverable` | Weekly meeting summary deliverable |
| `scenario_06_multiple` | Two simultaneous requests |
| `scenario_07_noisy` | Noisy / informal language (weather check) |
| `scenario_08_owner_in_text` | Owner name mentioned in document text |

Additional scenarios (`09_priority_words`, `10_failureish`) may be defined in `evaluation/test_scenarios.json`.

---

### `analysis.py` — Meeting Summarizer

Implements `generate_analysis(raw_text, items, meeting_date)` called by `SummaryAgent`.

Uses regex and heuristics to extract:
- **Meeting summary** — condensed narrative
- **Decisions made** — statements indicating resolved outcomes
- **Key topics** — dominant subjects
- **Participants** — unique speaker names from transcript
- **Next steps** — forward-looking statements

---

### `baseline_single_agent.py` — Baseline

A reference implementation of the same pipeline in a **single class**, without agent role separation or deduplication. Used for side-by-side comparison in the **Metrics** tab.

---

## 6. Streamlit UI (`app.py`)

```bash
streamlit run app.py
```

The app provides **7 tabs**:

| Tab | Contents |
|-----|----------|
| 📋 **Tasks** | Priority-badged task table with owner, deadline, category, confidence score badge |
| 🤖 **Agents** | Agent cards with active-agent highlighting and tool call summaries |
| 🔄 **State** | ASCII state diagram + full transition history with timestamps |
| 💬 **Messages** | Timestamped tool calls, agent messages, state transition log |
| 📊 **Metrics** | 5 metrics + priority distribution vs. baseline bar charts |
| 📄 **Logs** | JSONL event viewer + past run replay (select run by ID) |
| 📥 **JSON** | Structured output + download button |

### Authentication

The app uses `streamlit-authenticator` for login/signup. User credentials are stored in a local SQLite database (`meetings.db` via SQLAlchemy).

### Controls

- **Scenario selector** — choose from built-in or custom transcript
- **Seed input** — set seed for reproducible runs
- **▶ Start** button — runs the pipeline
- **⏹ Stop** button — graceful stop via `stop_flag`
- **Run 10 Scenarios** — triggers `run_evaluation()` and shows per-scenario table

---

## 7. Data Models

### `ActionItem` — Full Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | required | Unique task ID |
| `title` | `str` | required | Cleaned task title |
| `owner` | `str` | `"Unassigned"` | Responsible person |
| `deadline` | `str \| None` | `None` | ISO date or "ASAP" |
| `deadline_parse_method` | `str \| None` | `None` | How the deadline was inferred |
| `category` | `Literal[...]` | `"Other"` | Department category |
| `priority_score` | `int` | `1` | 1–10 urgency score |
| `priority_label` | `Literal[P1/P2/P3]` | `"P3"` | Priority tier |
| `dependencies` | `list[str]` | `[]` | Blocking task IDs |
| `status` | `Literal[...]` | `"Pending"` | Task status |
| `source_speakers` | `list[str]` | `[]` | Source speaker names |
| `confidence_score` | `float` | `0.0` | Action item confidence (0–1) |
| `priority_rule_hits` | `list[str]` | `[]` | Scoring rules that fired |

### Master JSON Output Format

```json
{
  "tasks": [
    {
      "task_id": "T001",
      "title": "Send the updated deck to the client",
      "owner": "Bob",
      "deadline": "2026-02-28",
      "category": "Sales",
      "priority": "P2",
      "score": 6,
      "confidence": 0.9
    }
  ]
}
```

### Log Event Format (JSONL)

```json
{
  "run_id": "a3f9bc12e4d7",
  "ts": "2026-02-27T17:45:23.412Z",
  "type": "state_transition",
  "payload": {
    "timestamp": "2026-02-27T17:45:23.412Z",
    "previous_state": "PARSING",
    "event": "tasks_extracted",
    "next_state": "TASKS_EXTRACTED"
  }
}
```

---

## 8. Guardrails & Safety

```
Tool called by agent
    │
    ├─▶ validate_tool_call(tool_name)
    │       [raises ValueError if not in ALLOWED_TOOLS]
    │
    ├─▶ with TimeoutGuard(10s, tool_name):
    │       tool_function(...)
    │       [raises ToolTimeoutError if > 10s]
    │
    ├─▶ validate_output(items)
    │       [Pydantic validation on all outputs]
    │
    ├─▶ StateMachine._guard_max_steps(event)
    │       [raises RuntimeError if > max_steps]
    │
    └─▶ stop_flag check between agents
            [graceful STOPPED transition]
```

| Guardrail | Class/Function | Default |
|-----------|---------------|---------|
| Tool allowlist | `validate_tool_call()` | 6 allowed tools |
| Output validation | `validate_output()` | Pydantic `ActionItem` |
| Timeout | `TimeoutGuard` | 10 seconds per tool |
| Step budget | `StateMachine.max_steps` | 20 steps |
| Human override | `stop_flag["stop"]` | Checked between agents |

---

## 9. Observability & Logging

Every call to `run_pipeline()` generates:

1. **`runs/<run_id>.jsonl`** — append-only event log

| Event Type | When |
|---|---|
| `run_start` | Pipeline begins |
| `state_transition` | Each state change |
| `agent_invoke` | Each agent called (with input hash) |
| `tool_call` | Before each tool (with input summary) |
| `tool_result` | After each tool (with output summary) |
| `message` | Agent completion messages |
| `metrics` | Final metrics dict |
| `run_end` | Pipeline ends (`ok` / `error` / `stopped`) |

2. **`runs/<run_id>.summary.json`** — compact summary for quick review

```json
{
  "run_id": "a3f9bc12e4d7",
  "metrics": { ... },
  "output_json": { "tasks": [...] }
}
```

Past runs can be replayed in the **Logs** tab or via:

```python
from src.logging_utils import replay_run
events = replay_run("runs", "a3f9bc12e4d7")
```

---

## 10. Evaluation & Metrics

### Run All Scenarios

```bash
python -m src
```

Outputs:

```
[1] Reproducibility check (seed=42)...
   ✅  SAME output for both runs (seed=42)

[2] 10-scenario evaluation (seed=7)...
   scenario_01_basic         items=3  owner=100%  deadline=100%  p1=0%   conf=0.72
   ...
   ─────────────────────────────────────────────────────
   MEAN  owner=100%  deadline=90%  p1=13%  conf=0.80  jaccard=0.52
```

### Aggregate Results (seed = 7)

| Metric | Value |
|--------|-------|
| Scenarios | 10 |
| Mean Owner Rate | ~100% |
| Mean Deadline Rate | ~90% |
| Mean P1 Rate | ~13% |
| Mean Confidence | ~0.80 |
| Jaccard vs Baseline | ~0.52 |

A Jaccard of ~0.52 indicates meaningful divergence — the multi-agent pipeline produces cleaner, deduplicated titles vs. the baseline's raw phrasing.

---

## 11. Reproducibility

Every run is fully deterministic given the same `seed`:

```python
from src.orchestrator import run_pipeline, RunConfig
from datetime import date

cfg = RunConfig(seed=42, meeting_date=date(2026, 2, 27))
out1 = run_pipeline("Alice: @Bob send the deck by Friday", cfg)
out2 = run_pipeline("Alice: @Bob send the deck by Friday", cfg)

assert [i.title for i in out1.items] == [i.title for i in out2.items]   # ✅ SAME
assert [i.owner for i in out1.items] == [i.owner for i in out2.items]   # ✅ SAME
assert [i.deadline for i in out1.items] == [i.deadline for i in out2.items]  # ✅ SAME
```

**Why it's deterministic:**
- All tools use regex pattern matching — no external LLM calls
- `ToolContext.seed` and `StateMachine.rng` are seeded from the same value
- `dateutil.parser` operates deterministically given a fixed `default` datetime
- No filesystem or network side effects in tool functions

---

## 12. Environment Variables

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | ❌ No | Optional API key — not used in local deterministic mode |

---

## 13. Running the CLI Evaluation

```bash
# Full evaluation (reproducibility check + 10 scenarios)
python -m src

# Or import programmatically
from src.evaluation import run_evaluation
result = run_evaluation(seed=7)
print(result.mean_owner_rate)
```

---

## 14. Demo Script (5–7 min)

1. Open `docs/architecture.md` — walk through agent roles & state machine
2. Launch `streamlit run app.py`, set **Seed = 7**
3. Select **scenario_09_priority_words** → click **▶ Start**
4. Walk through each tab:
   - **Tasks** — priority badges, owner/deadline/category
   - **Agents** — which agent is highlighted
   - **State** — transition history
   - **Messages** — tool call log
   - **Metrics** — 5 metrics + bar charts vs. baseline
5. Click **Run 10 Scenarios** → per-scenario table in Metrics tab
6. Reset, re-run same seed → compare JSON output (should be identical)
7. Select **scenario_10_failureish** (sparse/noisy) → show graceful handling with `deadline=null`

---

## 15. Team & Contribution

| Member | Role |
|--------|------|
| **Sumukh S P** | Team Lead, Architecture, Orchestrator & State Machine |
| **Harikrishna** | Backend – Tool implementations (`tools.py`) |
| **Supreeth S** | Agent design (`agents.py`, `guardrails.py`) |
| **Pruthvi R** | Evaluation harness & metrics (`evaluation.py`, `scenarios.py`) |
| **Vaishnavi Pralhad Shindhe** | Streamlit UI (`app.py`) |
| **Sukeerti Vani Jha** | Logging, analysis & documentation |

---

## Dependencies

```
streamlit==1.41.1
pydantic==2.10.5
python-dateutil==2.9.0.post0
streamlit-authenticator==0.4.1
SQLAlchemy==2.0.30
```

---

## License

See [LICENSE](../LICENSE).
