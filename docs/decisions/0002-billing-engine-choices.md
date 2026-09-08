# 0002 - Billing engine: cycle consumption and tariff selection tie-breaks

**Status:** Decided (Phase 2 - billing engine)

## Context

PRP.md FR-005/FR-007 require summing a meter's consumption for its active
billing cycle and picking the tariff plan effective for that period, but
leave two mechanical details unspecified.

## Decisions

**1. Cycle consumption = sum of each reading's already-computed
`eb_balance` within the cycle window**, rather than a separate
"closing reading minus opening reading" lookup. Each reading's `eb_balance`
is already "this reading minus its true chronological predecessor"
(see `app/domain/readings.py`), so summing consecutive balances within a
date range telescopes to exactly `closing - opening` for that range. This
reuses already-validated, already-tested logic instead of a second
calculation path that could disagree with it.

A reading with no balance yet (a meter's very first-ever reading, with no
predecessor at all) contributes 0 - there is no usage data from before
tracking began, so it is excluded rather than treated as an error.

**2. If more than one active tariff plan's effective-date range covers the
target date** (an unusual but possible configuration state), the plan with
the latest `effective_from` is selected - the most recently issued
applicable order wins. Overlapping plans are not treated as a hard error,
since an admin correcting a plan's dates might briefly create an overlap.

## Consequences

- No duplicate "what did this meter consume" calculation to keep in sync.
- Tariff selection is deterministic even if tariff plan date ranges are
  accidentally left overlapping, rather than raising for that case.
