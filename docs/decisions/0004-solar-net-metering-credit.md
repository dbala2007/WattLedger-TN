# 0004 - Solar generation credits the bill as a net-metering offset

**Status:** Decided (Phase 2 - billing engine)

## Context

CLAUDE.md section 7 already tracks a daily solar reading/balance per meter,
and the Billing screen showed the cycle's total solar generation, but that
number never affected the estimated bill - the tariff engine only ever
looked at EB (grid) consumption. For a household with an on-grid (grid-tied)
solar setup, the whole point of tracking solar separately is that it should
reduce what's owed: units fed back to the grid offset units drawn from it.

## Decision

`calculate_bill` now accepts an optional `solar_units_generated` value. After
the subsidy rule's free units are subtracted (producing "chargeable units"
exactly as before), solar generation is subtracted from that same number -
never below zero, and the actual amount applied is recorded separately as
`solar_units_offset` on the breakdown (CLAUDE.md section 5's "show every
part of the calculation" rule), since it can be less than the total solar
generated if generation exceeds what was left to charge for.

`billing_service.estimate_current_bill` only passes a non-zero value for a
meter whose `solar_mode` is `ON_GRID`. `OFF_GRID` meters get no credit here:
off-grid solar is consumed before the EB meter ever sees it, so it's already
reflected in a lower `eb_balance` - crediting it again here would double count it.
A `NONE`-solar meter never has solar readings to credit in the first place.

Which subsidy rule/slabs apply is still decided by the *gross* EB total, not
the post-solar figure - the government's free-unit threshold is based on
what was actually drawn from the grid, not net of self-generation.

## Consequences

- A grid-tied solar household's estimated bill now reflects the value of
  its solar generation, not just its EB draw.
- The UI shows a new "Solar credit applied" line (only for `ON_GRID`
  meters) between "Free/subsidized units" and "Chargeable units", matching
  the actual order of the calculation.
- If off-grid metering is ever modeled more precisely (CLAUDE.md section 7's
  future fields - grid import/export, net meter reading, self-consumed
  solar), this on/off-grid distinction will need revisiting rather than
  assumed away.
