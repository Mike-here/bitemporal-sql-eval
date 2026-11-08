# As-of Ledger Eval — development checkpoint

This eval measures whether models can reconstruct historical order state using
separate business-time and knowledge-time cutoffs. Late arrivals and retroactive
corrections make plausible SQL silently choose the wrong version, affecting
reconciliation and historical order-book reports.

**Status:** t01 implemented; t02–t06 planned. No live model trials have been run.
Human review, empirical findings, submission description and video are pending.
This checkpoint is not the final hackathon submission.

## Domain and expertise

The participant reports strong SQL optimization and financial order-book state
engine experience. All task data is newly generated synthetic data. The participant
must personally audit each task, reference answer and grader before submission;
see `reference/t01/review.md`.

## Setup and offline verification

Requirements: Python 3.13, uv and Git. SQLite >= 3.37 (STRICT support is not required;
window functions and SQLite authorizer/limit APIs are used). The tested interpreter
and SQLite versions are recorded in the checkpoint report. Lock dependencies:

```bash
uv sync --locked
uv run pytest
uv run python scripts/validate_t01.py
uv run python -m harness.run --task t01 --sql reference/t01/solution.sql --output work/reference-check.json
```

The output file must not already exist. Offline verification requires no API key
and incurs no model cost. Tests exercise manual goldens, seeded histories,
alternative SQL formulations, realistic semantic mutations, formatting, exact
integer comparisons and query execution restrictions.

## t01 contract and grading

Each version is a complete replacement state. Apply both inclusive cutoffs to
form the eligible relation; then select each order's greatest effective timestamp,
breaking an effective-time tie by greatest recorded timestamp. Zero quantity is
retained. Storage IDs do not order state. No tombstones/tenants exist in t01.

`tasks/t01/prompt.md` plus `schema.sql` is exactly the public model input. References,
fixtures and graders never enter the request. The submitted artifact is SQL; the
grader checks the result, not the SQL text or construction process. Row order and
alias case are ignored; duplicate rows, identifier case, exact values and column
order are preserved. Integers are never normalized through float. A task passes
only if every fixture passes; fixture fraction is a diagnostic, not partial primary
credit or independent observations.

There are 16 manually specified golden fixtures and 24 deterministic seeded
histories. The independent oracle replays Python datetime-ordered events; the SQL
reference ranks eligible rows with a window function. Manual golden expectations
are supplied separately from both implementations. Finite fixture validation
does not prove arbitrary SQL equivalence or universal absence of grader errors.

## Model configuration and live runs

`configs/models.json` requests `gpt-6-astra`, `gpt-6.1-sol`, and `gpt-6-luna`, all
with high reasoning effort and an 8,192-token output cap. Temperature is omitted.
The [official model catalog](https://developers.openai.com/api/docs/models) and
individual model pages were checked on 2026-11-08. Account access is unverified.
These IDs are documented request IDs, not immutable dated snapshots. The harness
records the returned model ID and raw response. This is a within-family comparison.

Set `OPENAI_API_KEY` in your shell (never commit its value). `.env.example` is a
template only; the runner does not auto-load it. A deliberate live command incurs
API usage; configure budget/quota before running:

```bash
uv run python -m harness.run --task t01 --model astra --trials 3 --output transcripts/t01-astra-pilot.jsonl
uv run python -m harness.replay transcripts/t01-astra-pilot.jsonl
```

Every trial is a fresh Responses request with no tools or conversation state.
There are no automatic retries. JSONL records contain the public request, response,
usage, timestamps, runtime, environment, source hashes and deterministic grades.
API errors and incomplete responses remain separate from semantic failures.
Output files are created exclusively and cannot silently overwrite earlier runs.
Saved completed outputs can be regraded offline; exact replay rejects changed hashes.
It also rejects a changed SQLite version rather than silently treating it as an
exact replay on the recorded runtime.

## Results, cost and runtime

No empirical model results or live costs yet. Planned formal design is six tasks,
three models and three trials per task: 54 attempts. Development/pilot runs must be
labeled separately. Local reference checks are not model performance results.
Aggregate reporting is deferred until real runs exist. Exact generations may vary
on live reruns; saved-output grading is deterministic on the recorded runtime.

## Main Failure Mode & Hot Take

Hypothesis only: models may confuse "latest known arrival" with "latest effective
state among visible records," or rank before restricting visibility. An empirical
hot take will be written only after reviewing actual failure transcripts.

## Prior work, sources and AI Use Disclosure

Task contracts, fixtures, references and harness were created for this event. No
existing benchmark tasks or confidential records are included. Standard bitemporal
concepts and [SQLite window functions](https://www.sqlite.org/windowfunctions.html)
are prior technical foundations. API integration follows the
[OpenAI text generation documentation](https://developers.openai.com/api/docs/guides/text).
Python, SQLite, pytest and httpx are third-party dependencies with their own licences.

Codex drafted the code, task language, synthetic fixtures, SQL reference, Python
oracle and initial documentation. Automated cross-checks validate the two independent
implementations against explicit goldens and test deliberately wrong queries.
Participant human review is pending and must not be represented as completed.

## Submission materials still required

Human signoff; five further tasks; frozen multi-trial model results and failure
analysis; approximate live cost/runtime; final short description; a <=5 minute
video link that opens without permission; final clean-environment ZIP verification.
