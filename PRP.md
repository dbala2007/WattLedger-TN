# PRP.md — WattLedger TN Product Requirements Prompt

## Purpose

This file is the living product-requirements document for WattLedger TN.

Claude should use it to:

- understand the product
- identify missing requirements
- record decisions
- propose implementation phases
- prevent assumptions from becoming hidden business rules
- prepare implementation plans for features
- keep desktop, web, mobile, synchronization, Tamil Nadu tariff rules, and solar support compatible

When an important requirement is unclear, Claude should add it to **Open Questions** and recommend a default. Do not block low-risk implementation unnecessarily.

---

# 1. Product Summary

WattLedger TN records daily cumulative household electricity and solar meter readings and turns them into daily consumption, billing-cycle usage, and estimated Tamil Nadu electricity charges.

The product begins as a no-login desktop application.

Long-term clients:

- Windows desktop
- Web
- Android/iOS mobile

Long-term data model:

- synchronized through a central API/database
- authenticated users
- multiple devices
- multiple meters/properties possible

Production hosting target:

- Hostinger VPS
- Docker

Primary geography:

- Tamil Nadu, India

Initial tariff category:

- Domestic / household

---

# 2. User Story — Daily Reading

As a household user,
I want to enter today's cumulative EB meter reading and solar reading,
so that the application automatically calculates today's consumption and updates the current billing-cycle estimate.

Fields:

- Meter No
- Solar Mode: None / On Grid / Off Grid
- Date
- EB Units
- EB Balance — calculated
- Solar Unit
- Solar Balance — calculated

Example:

Previous day:
- EB Units = 12,500.4
- Solar Unit = 4,200.0

Today:
- EB Units = 12,508.9
- Solar Unit = 4,207.5

Calculated:
- EB Balance = 8.5 units
- Solar Balance = 7.5 units

The user should not need to manually calculate these differences.

---

# 3. Core Functional Requirements

## FR-001 Meter Management

The user can:

- create a meter
- edit meter details
- activate/deactivate a meter
- select solar mode
- configure billing-cycle reference information

Meter number must not be assumed globally unique across all future providers, so use an internal ID.

## FR-002 Daily Reading Entry

The user can add one daily reading per meter.

The system calculates balances using the previous chronological reading.

## FR-003 Historical Editing

The user can edit/delete a prior reading.

The system recalculates affected subsequent balances.

## FR-004 Reading History

Provide:

- date
- EB cumulative reading
- EB daily balance
- solar cumulative reading
- solar daily balance
- edit/delete controls

Filters:

- meter
- date range

## FR-005 Billing Cycle

For each meter, determine the active billing period and aggregate EB consumption.

Do not rely only on calendar months.

## FR-006 Tariff Management

The user/admin can:

- view tariff versions
- add a tariff version
- edit configuration
- define slabs
- define threshold-specific rule groups
- define subsidy/free-unit rules
- set effective dates

Never destroy old versions that were used historically.

## FR-007 Bill Estimate

For the active billing cycle calculate:

- consumed units
- free/subsidized units
- chargeable units
- slab-by-slab cost
- additional configured charges
- estimated total

Store enough data to explain the result.

## FR-008 Dashboard

Show at minimum:

- today's EB consumption
- today's solar balance
- current-cycle EB units
- estimated current bill
- last reading date
- usage trend

## FR-009 Multiple Meters

The architecture must support multiple meters, even if Phase 1 UI starts with one.

## FR-010 Backup

Before cloud synchronization exists, support an easy local backup/restore mechanism.

---

# 4. Tamil Nadu Tariff Requirement

## Billing frequency

Domestic EB assessment is normally bi-monthly.

The application's billing engine should treat the cycle as a meter-specific period rather than blindly grouping two calendar months.

## Current free-unit rule to seed

Effective 10 May 2026:

- Domestic consumption up to 500 units per bi-monthly cycle: 200 free units for eligible consumers
- Consumption above 500 units: existing structure continues, including 100 free units

This must be configurable and effective-dated.

## Tariff slabs

Slab rates are regulatory/configuration data.

Do not permanently encode them in source code.

A tariff version should support different slab groups based on total cycle consumption, because Tamil Nadu domestic charging can use different slab treatment depending on the total consumption band.

Example conceptual configuration:

```yaml
tariff_version:
  name: "TN Domestic Example"
  effective_from: "YYYY-MM-DD"

rule_groups:
  - name: "cycle_upto_threshold"
    total_consumption_max: 500
    free_units: 200
    slabs:
      - from: ...
        to: ...
        rate: ...

  - name: "cycle_above_threshold"
    total_consumption_min: 500.0001
    free_units: 100
    slabs:
      - from: ...
        to: ...
        rate: ...
```

The exact current production slab table must be verified against the latest TNERC/TNPDCL source before release.

---

# 5. Solar Requirements

Initial definitions need confirmation.

Current interpretation:

`Solar Unit` = cumulative reading visible on the user's solar meter/inverter.

`Solar Balance` = current cumulative solar reading minus previous cumulative solar reading.

However, on-grid solar can expose multiple quantities.

The future model should be ready to distinguish:

- solar generation
- grid import
- grid export
- net meter
- self consumption
- battery flows

Do not calculate monetary solar savings until the meaning/source of each meter reading is confirmed.

---

# 6. Non-Functional Requirements

## NFR-001 Cross-platform future

Do not couple business logic to desktop UI.

## NFR-002 Offline-friendly Phase 1

Desktop MVP should remain usable locally without internet.

## NFR-003 Synchronization future

The model should support switching from local SQLite to API/PostgreSQL without changing business meanings.

## NFR-004 Performance

Daily household readings are low volume, but queries should be indexed by:

- meter
- reading date
- billing period

## NFR-005 Data integrity

Consumption/bill calculations must be deterministic and testable.

## NFR-006 Auditability

The application must identify the tariff version used for any bill estimate.

## NFR-007 Locale

- India date-friendly display
- INR
- kWh
- timezone Asia/Kolkata

## NFR-008 Accessibility

Use readable labels and do not rely on color alone to communicate warnings or usage status.

---

# 7. Recommended Delivery Phases

## Phase 0 — Requirements + Skeleton

Deliver:

- final data definitions
- architecture
- repository
- backend skeleton
- frontend skeleton
- SQLite setup
- automated test setup

## Phase 1 — Desktop Reading MVP

Deliver:

- meter setup
- daily entry
- automatic balances
- history
- edit/delete
- validation
- dashboard basics

No login.

## Phase 2 — Billing Engine

Deliver:

- billing-cycle configuration
- tariff versions
- slab editor
- subsidy rules
- estimated bill
- detailed calculation breakdown
- tariff boundary tests

## Phase 3 — Reporting + Solar

Deliver:

- charts
- comparisons
- forecasts
- solar analytics
- exports
- backup/restore

## Phase 4 — Server + Sync

Deliver:

- PostgreSQL
- FastAPI deployed on VPS
- Docker Compose
- migrations
- synchronization strategy
- secure API

## Phase 5 — Accounts

Deliver:

- signup
- login
- password reset
- household/meter ownership
- authorization
- account management

## Phase 6 — Web + Mobile

Deliver:

- Flutter web build or agreed web approach
- Android
- iOS if required
- synchronization testing across clients
- responsive/adaptive layouts

---

# 8. Acceptance Criteria — Daily Entry MVP

Given a meter with yesterday's EB reading of 1000.0,
when the user enters today's reading as 1008.5,
then the app saves EB Balance as 8.5.

Given yesterday's solar reading of 500.0,
when today's solar reading is 506.2,
then Solar Balance is 6.2.

Given today's EB reading is lower than the prior cumulative reading,
the app must warn and prevent normal save unless a supported meter-reset/replacement flow is used.

Given a backdated reading is inserted,
balances of chronologically affected readings are recalculated.

Given a non-solar meter,
solar fields are not required.

---

# 9. Acceptance Criteria — Billing

Given a configured tariff version,
the estimate must select the version effective for the billing period.

Given total consumption exactly matches a subsidy threshold,
the correct threshold rule is used.

Given total consumption is one unit above the threshold,
the correct alternate rule is used.

The result must show a slab-by-slab breakdown.

Changing today's tariff must not change previously finalized historical assessment calculations unless the user explicitly recomputes them.

---

# 10. Data Migration Strategy

Phase 1 can use SQLite.

Before cloud synchronization:

1. Introduce schema migrations.
2. Normalize all important entities.
3. Ensure IDs are portable.
4. Add created/updated timestamps.
5. Migrate to PostgreSQL.
6. Test old SQLite data export/import.
7. Only then introduce user ownership/sync.

Avoid storing critical structured data only in JSON blobs.

---

# 11. API Candidates

Future endpoints may include:

```text
GET    /meters
POST   /meters
GET    /meters/{id}
PATCH  /meters/{id}

GET    /meters/{id}/readings
POST   /meters/{id}/readings
PATCH  /readings/{id}
DELETE /readings/{id}

GET    /meters/{id}/billing-cycle/current
GET    /meters/{id}/bill-estimate

GET    /tariffs
POST   /tariffs
GET    /tariffs/{id}
PATCH  /tariffs/{id}

POST   /auth/signup
POST   /auth/login
POST   /auth/refresh
```

Do not implement all endpoints at once. Add them only as required by the current phase.

---

# 12. Open Questions Claude Must Resolve/Track

Use this section as a living requirements interview.

## Meter / EB

- [ ] Is "Meter No" the physical meter serial number, TNPDCL service/consumer number, or either?
- [ ] Can one property have multiple EB meters?
- [ ] Should meter number be masked in screenshots/exports?
- [ ] Are readings always kWh, or can the meter display decimals?
- [ ] What should happen when the physical meter is replaced/reset?
- [ ] Should the app store the photo of the meter reading as evidence?
- [ ] Should users be able to skip days? Assumed: yes.
- [ ] If days are skipped, should the balance be shown as "usage since previous reading" rather than "daily usage"? Recommended: yes.

## Billing

- [ ] How will the initial billing-cycle start/end date be obtained?
- [ ] Should the user enter the official TNPDCL assessment date after every bill?
- [ ] Should the application store official bill amount for estimate-vs-actual comparison?
- [ ] Are meter/service fixed charges required for the household tariff being tracked?
- [ ] Should electricity tax/other adjustment lines be supported?
- [ ] Should tariff updates require user confirmation before becoming active?
- [ ] Should the app offer a "copy previous tariff and revise" workflow?
- [ ] Should bill estimates be rounded exactly like TNPDCL? Need verified rounding rules.

## Current Tamil Nadu tariff

- [ ] Re-verify the latest TNERC tariff order before production release.
- [ ] Re-verify the latest TNPDCL domestic billing calculator/result.
- [ ] Confirm exact slab values currently passed to domestic customers after government subsidy.
- [ ] Confirm how the 200-free-unit scheme interacts with each slab for <=500-unit cycles.
- [ ] Confirm the >500-unit calculation and 100-free-unit treatment.
- [ ] Record order/source and effective date in tariff configuration.

## Solar

- [ ] What exact device provides "Solar Unit"?
- [ ] Is Solar Unit total generated energy or exported-to-grid energy?
- [ ] For on-grid systems, should grid import and export be separate fields?
- [ ] Is there a bidirectional/net meter?
- [ ] Should inverter readings and TNPDCL net-meter readings both be recorded?
- [ ] For off-grid systems, should battery SOC be recorded?
- [ ] Should battery charge/discharge be tracked?
- [ ] Should the app estimate money saved by solar?

## UX

- [ ] Windows only for the first desktop build?
- [ ] Should the reading entry screen open by default?
- [ ] Is manual date selection required or default to today?
- [ ] Is Tamil language support required?
- [ ] Should light/dark mode be supported?
- [ ] Should reminders be added for daily reading?
- [ ] Should the app show alerts when projected cycle usage approaches a tariff threshold?

## Backup / Import

- [ ] Preferred backup format: SQLite copy, ZIP, JSON, CSV, or multiple?
- [ ] Need Excel export?
- [ ] Need import from an existing spreadsheet?
- [ ] Should backups be encrypted after accounts are introduced?

## Authentication / Sync

- [ ] Email/password only initially?
- [ ] Google login later?
- [ ] Can multiple family members access one household?
- [ ] Which roles are required: owner/member/viewer?
- [ ] How should offline edits synchronize when two devices changed the same reading?
- [ ] Is real-time synchronization necessary or eventual sync sufficient?

## Hosting

- [ ] Confirm Hostinger VPS OS.
- [ ] Confirm domain/subdomain.
- [ ] Existing Nginx/Caddy/Traefik?
- [ ] Existing PostgreSQL instance or create dedicated container/database?
- [ ] Required backup retention.
- [ ] Monitoring/logging requirements.

---

# 13. Claude Feature Planning Template

Before implementing any feature larger than a trivial UI change, Claude should produce:

## Feature

Name:

## User problem

What problem does this solve?

## Requirements

- ...
- ...

## Assumptions

- ...

## Open questions

- ...

## Data model impact

- ...

## API impact

- ...

## UI impact

- ...

## Business rules

- ...

## Validation/errors

- ...

## Security/privacy impact

- ...

## Tests

- ...

## Migration/backward compatibility

- ...

## Implementation sequence

1. ...
2. ...
3. ...

## Definition of done

- ...

---

# 14. Initial Decisions

| Decision | Current choice | Status |
|---|---|---|
| Product name | WattLedger TN | Proposed |
| Initial platform | Desktop | Confirmed requirement |
| Initial authentication | None | Confirmed requirement |
| Future sync | Yes | Confirmed requirement |
| Future web | Yes | Confirmed requirement |
| Future mobile | Yes | Confirmed requirement |
| Backend | FastAPI/Python | Recommended |
| Desktop/web/mobile UI | Flutter | Recommended |
| Local DB | SQLite | Recommended |
| Production DB | PostgreSQL | Recommended |
| Deployment | Docker on Hostinger VPS | Confirmed requirement |
| Python package manager | uv | Preferred |
| Billing region | Tamil Nadu | Confirmed requirement |
| Billing cycle | Bi-monthly | Confirmed requirement |
| Tariff management | Effective-dated/editable | Required |
| Solar modes | None/On-grid/Off-grid | Required |

Update this table whenever a decision changes.

---

# 15. First Implementation Target

Do not begin with authentication, cloud sync, graphs, or Docker deployment.

The first vertical slice should be:

1. Create one meter.
2. Enter first EB reading.
3. Enter second EB reading.
4. Automatically calculate the difference.
5. Repeat for solar when enabled.
6. Display reading history.
7. Edit a reading and verify recalculation.
8. Add automated tests.

Once this is stable, implement the tariff/billing-cycle engine.
