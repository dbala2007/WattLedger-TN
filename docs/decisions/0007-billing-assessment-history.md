# 0007 - Billing history from recorded meter reader visits

**Status:** Decided (Phase 2 - billing history / official-bill comparison)

## Context

Users could only see the *current* billing cycle's bill. There was no way
to check the previous cycle, because the only record of a cycle boundary
was `Meter.last_assessment_date` - a single field that is overwritten on
every new visit. Once the meter reader came again, the old cycle's start
date was lost (ADR 0003 noted this as future work).

CLAUDE.md section 10 planned a `BillingAssessment` entity for this.

## Decision

1. **New `BillingAssessment` table** - one row per official TNPDCL
   assessment (meter reader visit) per meter: `assessed_on` (unique per
   meter), optional `official_bill_amount`, optional `notes`.
2. **Cycles are derived, not stored.** Consecutive visits define the
   completed cycles: visit A to visit B is the cycle `A .. B-1`
   (`domain.billing_cycles.completed_cycles_from_assessments`), keeping
   the "one day belongs to exactly one cycle" rule. N visits give N-1
   completed cycles; the latest visit opens the current cycle.
   Storing only visit dates (not start/end pairs) means gaps and
   overlaps between cycles are impossible by construction.
3. **Consumption and estimates are recalculated live**, not stored.
   CLAUDE.md section 10 listed `opening_reading`, `closing_reading`,
   `consumed_units` and `estimated_amount` columns; they are deliberately
   left out, because stored copies would go stale whenever a historical
   reading is edited (CLAUDE.md section 4 requires edits to recalculate
   affected values). The official amount lives on the *closing* visit,
   since that visit is when TNPDCL raises the bill for the cycle that
   just ended.
4. **Past cycles are priced with the tariff effective on the cycle's last
   day**, not today's tariff (CLAUDE.md section 5). The running cycle is
   still priced as of today, as before. If no tariff covers an old cycle,
   it is still listed with units and a note instead of failing the list.
5. **`Meter.last_assessment_date` is kept as a synced copy** of the
   latest visit, so `get_current_cycle_for_meter` and already-installed
   app versions keep working. Every visit create/edit/delete re-syncs it;
   a `next_expected_assessment_date` that is no longer after the latest
   visit is cleared. The older way (PATCH `last_assessment_date` on the
   meter) still works and records a visit if that date is not yet in the
   history. The Edit Meter screen now only *displays* the latest visit;
   visits are managed from Billing > Billing history.
6. **Migration:** `create_all` creates the new table on startup (SQLite
   and PostgreSQL - no existing table changes). A startup backfill copies
   each meter's existing `last_assessment_date` into the history once,
   so current cycles don't move.

API:

```text
GET    /meters/{id}/billing-history          completed cycles, newest first
GET    /meters/{id}/assessments
POST   /meters/{id}/assessments
PUT    /meters/{id}/assessments/{aid}        full replace (can clear amount/notes)
DELETE /meters/{id}/assessments/{aid}
```

## Consequences

- Previous cycles are visible with the full slab breakdown, and
  estimate-vs-official comparison exists (a Phase 2 item).
- The user must record the visit that *started* a cycle as well as the
  one that ended it before that cycle appears.
- Editing a tariff plan **in place** changes history estimates for the
  cycles it covers (adding a new effective-dated version does not).
  PRP.md section 9's "finalized historical assessment" criterion is
  therefore only partly met; tracked in PRP.md Open Questions.
- A mid-cycle tariff change is not prorated - the whole cycle uses the
  tariff effective on its last day. Also tracked as an open question.
