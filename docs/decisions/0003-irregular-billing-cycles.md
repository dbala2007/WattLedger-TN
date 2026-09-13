# 0003 - Billing cycles are corrected by real assessment dates, not fixed intervals

**Status:** Decided (Phase 1/2 - billing cycle)

## Context

CLAUDE.md section 6 already warned that a meter's cycle does not necessarily
start on the first of an odd/even month, and asked for `last_assessment_date`
/ `next_expected_assessment_date` fields with "manual correction" support.
Those fields existed on `Meter` and were already editable in the Add/Edit
Meter screen, but `get_current_cycle_for_meter` never actually read them -
it only ever computed the cycle by stepping `billing_cycle_reference_date`
forward/backward by a fixed `cycle_length_months`.

In practice, TNPDCL/TANGEDCO's bi-monthly billing is not a fixed interval:
the cycle boundary is whichever day the meter reader actually visits, so
real cycles run anywhere from, say, 55 to 70 days rather than exactly two
calendar months. Editing the assessment-date fields had no effect on the
computed cycle window or the bill estimate, which was silently wrong for
any household whose actual cycle drifted from the fixed-interval guess.

## Decision

`get_current_cycle_for_meter` now prefers the user's corrected dates over
the fixed-interval calculation, entirely:

- If `last_assessment_date` is set, it - not `billing_cycle_reference_date`
  arithmetic - is the authoritative start of the current cycle.
- The end is `next_expected_assessment_date` (minus one day, to keep the
  existing "one calendar day belongs to exactly one cycle" convention) if
  the user has entered their own correction/estimate of the next visit, or
  a `cycle_length_months`-based placeholder otherwise - kept only until the
  user corrects it once the real date is known.
- A meter that has never had an assessment date recorded still falls back
  to the original fixed-interval calculation unchanged, so nothing behaves
  differently until someone actually corrects a date.

`meter_service.update_meter` rejects a `next_expected_assessment_date` that
is on or before `last_assessment_date`, since that would describe a
zero-or-negative-length cycle.

## Consequences

- Consumption and bill estimates are computed against the real cycle a
  household is actually billed on, once they've recorded it, instead of an
  arithmetic guess that quietly drifts out of sync with reality.
- No schema change and no frontend change were needed - the assessment-date
  fields and their edit UI already existed; only the domain calculation
  that had never consumed them needed to change.
- A meter with a corrected `last_assessment_date` ignores `as_of_date` when
  deciding the cycle window (there is only one "current" cycle to describe,
  not a repeating pattern to evaluate at an arbitrary point in time). Per-cycle
  history with its own stored dates is still future work (`BillingAssessment`,
  CLAUDE.md section 10/12) - today only the *current* cycle can be corrected.
