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
- t03: late retroactive corrections and historical knowledge visibility.
- t04: revision/sequence tie-breaks and idempotent duplicate ingestion.
- t05: tenant/book composite identity and cancellation-key scope.
- t06: snapshot-before-aggregation with specified empty/zero groups.

Only t01 is implemented. Later tasks require their own explicit contracts and
distinct practitioner interactions; they must not merely clone t01 fixtures.

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

One OpenAI family supports a scale comparison, not a claim about all frontier
families. General correctness of arbitrary SQL is not proven by finite fixtures.
SQLite execution is a query-only boundary, not a general native-code sandbox.
