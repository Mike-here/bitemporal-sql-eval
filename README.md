# As-of Ledger Eval — six-task development checkpoint

This eval measures SQL reconstruction of historical order state with separate
business-time and knowledge-time cutoffs. Late arrivals, restated amendments,
withdrawal states and composite identity can change the answer while plausible
queries still produce convincing reports. Reconciliation and financial order-book
reporting depend on getting these interactions right.

**Status:** all six tasks implemented and verified offline. Michael Acheampong
human-verified t01's prompt, SQL reference and Python oracle. t02–t06 await his
review. Three live t01 diagnostic attempts returned quota errors without producing
answers. No empirical model pass rates or frontier capability findings exist yet.
This is a development checkpoint, not the final hackathon submission.

## Domain, expertise and task overview

Michael Acheampong reports strong SQL schema/query optimization and financial
order-book state engine experience. All task data is newly generated synthetic
data; no employer/client records or existing benchmark tasks are included.

- **t01 — baseline:** full replacement versions, two inclusive cutoffs, out-of-order
  corrections. Its deliberately explicit recipe provides calibration.
- **t02 — withdrawals:** a governing DELETE removes an order; older active states
  must not reappear. Later UPSERTs can reopen it.
- **t03 — restated amendments:** a correction changes one amendment's meaning,
  including effective time. Obsolete revisions are not separate business events.
- **t04 — source precedence:** equal clocks require integer revision/sequence
  precedence, while retry deliveries have only one business effect.
- **t05 — scoped cancellation:** order identity and cancellation groups belong to
  a full tenant/book scope; current cancellation keys can differ from old keys.
- **t06 — net exposure:** scoped, restated and deduplicated order state becomes
  signed quantity/notional totals. The reporting roster includes empty tenants;
  zero net quantity does not imply zero active orders.

t02–t06 state business semantics/invariants without prescribing a SQL execution
recipe. Every graded type, identity, precedence, cutoff, empty-result and numeric
rule is in that task's prompt/schema. See `docs/task_design.md` and each task's
review record. Difficulty and a useful performance spread remain hypotheses until
measured; the suite has not been selected for particular model failures.

## Setup and offline reproduction

Requirements: Python 3.13, uv, SQLite >=3.37. Dependency versions/hashes are locked
in `uv.lock`; the verified local interpreter is Python 3.13.9 with SQLite 3.51.0.
From a clean extraction:

```bash
uv sync --locked
uv run pytest
uv run python scripts/validate_suite.py
uv run python -m harness.run --task t06 --sql reference/t06/solution.sql --output work/t06-reference.json
```

The requested output report must not already exist. Tests/verification are offline
and incur no model cost. They compare independent Python datetime/state oracles
with the reference SQL and different correct SQL formulations, check explicit
goldens and seeded histories, and reject targeted semantic mutations. Source
hashes and mutation examples are in `results/local_validation/suite.json`.
The suite covers 195 fixtures, including 91 explicitly specified golden outcomes,
and rejects 64 semantic mutants. These are not 195 independent model tasks.

Fixture regeneration scripts are provided in `scripts/`; do not regenerate or
alter task artifacts after a formal experiment is frozen. Independent references
and passing finite tests do not prove universal equivalence of arbitrary SQL.
Human audit remains required, especially for the five newly implemented tasks.

## Outcome grading and isolation

The model sees only a task's `prompt.md` plus `schema.sql`. Fixtures, expected
outcomes, references and graders never enter API input. Each candidate SELECT
runs on a fresh in-memory SQLite database per fixture. Public-table reads are
allowed; writes, attached files, extensions and metadata inspection are denied.
Resource bounds are stated in the prompt. This is a SQLite query boundary, not
a general-purpose native-code sandbox.

The grader compares complete result multisets, never a prescribed SQL method.
Alias case and row order are ignored; duplicate multiplicity, text identity,
column order and exact numeric values are preserved. Integer expectations are
never converted to floats. Each task attempt receives one binary primary score:
all fixtures must pass. Fixture fraction is diagnostic, not extra independent
observations or partial primary credit. Bad fixture/reference configuration raises
an infrastructure error rather than silently scoring a model failure.

## Credentials and live providers

Put `OPENAI_API_KEY` and optionally `GEMINI_API_KEY` in a local `.env`, or set them
in the environment. The root `.env` takes precedence. The safe loader recognizes
only these names and never executes shell interpolation. Do not share actual
values. `.env` is ignored by Git and excluded from the source allowlist/ZIP.

```bash
uv run python scripts/discover_models.py
uv run python -m harness.run --task t01 --model astra --trials 1 --phase diagnostic --output transcripts/diagnostic/new-t01-astra.jsonl
```

These deliberately selected commands contact providers; generation incurs usage.
Live catalogs were checked on November 8, 2026. OpenAI listed `gpt-6-astra`,
`gpt-6.1-sol`, and `gpt-6-luna`. Gemini's native `/v1beta/models` returned HTTP 401,
so no usable Gemini ID has been verified. Michael authorized the OpenAI fallback
while resolving Gemini credentials. The native Gemini adapter supports explicit
thinking configuration and has mocked tests, but no live Gemini inference.

The current matrix requests Astra and Sol as frontier models and Luna as the
smaller/faster comparison, all with high reasoning effort, an 8,192-token output
cap, no tools, and omitted temperature (provider default). These are exact request
IDs, not immutable dated snapshots; returned model IDs and timestamps are logged.
One provider/family cannot establish cross-family generality. Access is verified
by generation, not by appearing in a model catalog.

## Diagnostic pilot and empirical results

Each of the three t01 pilot requests is saved in `transcripts/diagnostic/` with
its public request, timestamps, source hashes and sanitized API error. All returned
HTTP 429 before producing SQL. A separately recorded 32-token setup probe returned
`credit_balance_exhausted` / `insufficient_quota`. It is not a benchmark attempt.
Catalog evidence and the probe are in `results/model_discovery/`.

There are **zero graded diagnostic outputs and zero formal trials**. We therefore
report no model pass rates, variance, empirical costs or capability conclusions.
The incomplete pilot does not validate live SQL extraction/grading end to end;
that path currently has offline/mock verification only. Provider quota and Gemini
authentication must be restored before completing it.

Formal design remains six tasks × three models × three trials = 54 attempts.
Every attempt starts with fresh context; no automatic retries or overwritten
logs. API failures, blocked responses and incomplete generations remain separate
from incorrect task outcomes. After freezing, preserve all attempts and rerun
affected comparisons if a task/grader changes. Report completion rate, per-task
success counts, overall pass rates and all-trials reliability with small-sample
limits. Record actual usage/cost/runtime when successful runs exist.

Saved completed outputs can be regraded with:

```bash
uv run python -m harness.replay path/to/transcript.jsonl
```

Exact replay rejects changed source hashes or SQLite versions. The original
diagnostic source snapshot is retained in `results/diagnostic/t01-pilot-code.zip`
because development continued after the attempted pilot. Extract that snapshot
to reproduce the original source context; error-only attempts have no SQL to grade.

## Main Failure Mode & Hot Take

Hypothesis: models may confuse latest arrival with current effective state,
resurrect withdrawals, retain obsolete amendment meanings, leak composite scope
or aggregate histories rather than reconstructed orders. An empirical hot take
must await successful runs and reviewed failure transcripts. Access/quota errors
are infrastructure findings, not evidence of a reasoning limitation.

## Prior work, provenance and AI Use Disclosure

Tasks, synthetic fixtures, references and harness were developed for this event.
Standard bitemporal concepts and [SQLite window functions](https://www.sqlite.org/windowfunctions.html)
are prior technical foundations. API adapters follow the
[OpenAI Responses/reasoning documentation](https://developers.openai.com/api/docs/guides/reasoning)
and [native Gemini generateContent API](https://ai.google.dev/api/generate-content).
Python, SQLite, pytest and httpx retain their respective third-party licences.

Codex drafted the task language, synthetic fixtures, SQL solutions, Python oracles,
graders, API adapters, tests and documentation. Michael Acheampong human-verified
the t01 prompt, SQL reference and Python oracle on November 8, 2026. Further
review scope is explicit in `reference/t01/review.md`; t02–t06 reviews are pending.
Automated verification is never represented as human expert verification.

## Remaining submission materials

Complete the live pilot; human-review t02–t06; freeze and execute the 54-run matrix;
analyze real transcripts; document measured cost/runtime and final findings;
write the short submission description; record a <=5-minute video and verify its
public link; then reproduce and verify the final <50 MB ZIP. The README must carry
the final video link and short description before submission.
