# Scope and hypothesis

Reconstruct order/ledger state as of a business-time cutoff with only information
available by a separate knowledge-time cutoff. The intrinsic difficulty is that
visibility, version precedence and state semantics interact: applying the right
operation at the wrong stage changes a financially consequential snapshot.

Participant expertise (self-reported): SQL schema/query optimization and financial
order-book state engines. No employer/client data is used; all fixtures are synthetic.

## Planned progression

- t01: full-state revisions, two inclusive cutoffs, out-of-order corrections.
- t02: tombstone precedence; do not resurrect an earlier active state.
- t03: late retroactive corrections to amendment identity, including changed effective timestamps.
- t04: revision/sequence tie-breaks and idempotent duplicate ingestion.
- t05: tenant/book composite identity and cancellation-key scope.
- t06: scoped amendment restatements, duplicates and withdrawal states before signed exposure aggregation; specified roster/empty/zero groups.

All six tasks are implemented. t01 has participant review; t02–t06 await review.
The later tasks use distinct practitioner interactions rather than cloned fixtures.

## Prompt design decision from participant review (2026-11-08)

t01 intentionally supplies an explicit eligibility/precedence recipe as baseline
calibration. For t02–t06, state complete business semantics and invariants instead
of a procedural SQL solution. Define visibility, identity, tombstone meaning,
revision precedence, duplicate equivalence and aggregation/empty-group behavior
where applicable, but leave the query's operation ordering to the model. Hidden
fixtures may exercise stated rules; they must not introduce unstated requirements.
Semantic interaction, rather than ambiguity, should supply the difficulty. The
presence of headroom must be established empirically, not assumed from prompt style.

## Experimental discipline

The requested high/partial frontier success and lower smaller-model success are
calibration hypotheses, not results. Start with one diagnostic pilot; preserve it
and label it development data. Freeze all task/config/grader/fixture hashes before
formal trials, and retain every formal attempt. If a task changes, disclose the
change and rerun affected formal comparisons. Never select only failed runs.

Primary score: one binary verdict per task attempt (all fixtures pass). Fixture
pass fraction is diagnostic and does not increase the experimental sample size.
Report 3 trials/task/model, per-task success counts, overall pass rates, and the
fraction of tasks passed on every trial. Provider errors and incomplete outputs
must be separately visible; report completion rate and end-to-end success as well
as success conditional on completion. Do not silently retry them.

The current matrix selects OpenAI Astra, Gemini 3.1 Pro Preview, and OpenAI Luna.
Both replacement keys authenticate to their catalogs, but generation remains
blocked by OpenAI exhausted credits and Gemini RESOURCE_EXHAUSTED. All six t01
diagnostic attempts returned API errors, not model answers, and are not scores.
General correctness of arbitrary SQL is not proven by finite fixtures.
SQLite execution is a query-only boundary, not a general native-code sandbox.
