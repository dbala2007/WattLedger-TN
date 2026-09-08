# CLAUDE.md — WattLedger TN

## 1. Project Identity

**Project name:** WattLedger TN

WattLedger TN is a Tamil Nadu household electricity and solar usage tracking application.

The application starts as a desktop application without authentication, but its architecture must support:

1. Desktop application — first release
2. Web application — later release
3. Mobile application — later release
4. Shared synchronized data across all clients
5. User signup/login when synchronization is introduced
6. Docker deployment on a Hostinger VPS

Do not design Phase 1 in a way that requires the business logic to be rewritten for web/mobile.

---

## 2. Primary User Goal

The user should be able to enter cumulative electricity meter readings each day and have the application automatically calculate:

- Daily EB consumption
- Daily solar generation/reading difference
- Current billing-cycle EB consumption
- Estimated EB bill based on Tamil Nadu domestic tariff rules
- Current tariff/subsidy rule used for the estimate
- Solar contribution and trends
- Historical daily/monthly/billing-cycle usage

The app is initially intended for household use in Tamil Nadu, India.

---

## 3. Core Data Fields

Each daily reading currently requires:

| Field | Description |
|---|---|
| Meter No | EB/TNPDCL meter/service identifier |
| Solar Mode | `NONE`, `ON_GRID`, or `OFF_GRID` |
| Date | Date on which the reading was captured |
| EB Units | Cumulative EB meter reading |
| EB Balance | Difference between current and previous EB reading |
| Solar Unit | Cumulative solar reading, when applicable |
| Solar Balance | Difference between current and previous solar reading |

### Important rule

`EB Balance` and `Solar Balance` are **calculated values**, not values the user normally types.

For a given meter:

`EB Balance = today's EB Units - previous chronological EB Units`

`Solar Balance = today's Solar Unit - previous chronological Solar Unit`

The application should calculate these values server-side/domain-side so all clients behave consistently.

---

## 4. Validation Rules

Implement these rules centrally in the domain/service layer:

- Meter number is required.
- Date is required.
- Only one active reading per meter per date unless explicitly supporting multiple readings later.
- EB Units cannot normally be lower than the prior cumulative EB reading.
- Solar Unit cannot normally be lower than the prior cumulative solar reading.
- Negative balances must trigger a warning/error and must not silently save.
- Allow a future "meter reset/replacement" workflow rather than treating a reset as normal consumption.
- Solar Unit is optional when `Solar Mode = NONE`.
- Solar Unit should normally be required when solar tracking is enabled.
- Decimal readings should be supported.
- Do not calculate a balance from insertion order; calculate from chronological previous reading.
- If an older/backdated reading is inserted, recalculate affected subsequent balances.
- Deleting or editing a historical reading must recalculate adjacent/affected balances.
- Store timestamps in UTC where timestamps are required, but store the user's reading date as a local calendar date.
- Default locale/timezone: `Asia/Kolkata`.
- Currency: INR.
- Energy unit: kWh ("units").

---

## 5. Tamil Nadu Billing Rules

Tamil Nadu domestic electricity billing is generally assessed on a bi-monthly cycle.

The tariff engine MUST NOT contain slab rates as permanent constants.

Create effective-dated tariff configuration tables so tariff versions can be:

- Added
- Edited
- Activated/deactivated
- Assigned an effective-from date
- Assigned an optional effective-to date
- Audited/versioned

### Current subsidy rule to seed for development

As of 10 May 2026, Tamil Nadu's domestic free-electricity scheme provides:

- Up to 500 units in a bi-monthly cycle: 200 free units for eligible domestic consumers
- More than 500 units in a bi-monthly cycle: the existing tariff structure continues, including 100 free units

This rule must be stored as editable configuration, not hard-coded.

### Tariff-source policy

Before changing the production default tariff:

1. Check the latest TNERC tariff order.
2. Check current TNPDCL/TANGEDCO billing guidance or calculator.
3. Record source name/order number/effective date in the tariff version.
4. Never silently overwrite an older tariff version.
5. Historical bills must continue using the tariff version effective during that billing cycle.

### Calculation transparency

For every estimate display:

- Total billing-cycle units
- Subsidized/free units applied
- Chargeable units
- Slabs applied
- Units charged in each slab
- Rate per slab
- Amount per slab
- Fixed/other charges if configured
- Total estimated bill
- Tariff version/effective date

Do not show only a final bill amount.

---

## 6. Billing Cycle

Do not assume every meter's cycle starts on the first day of an odd/even month.

Each meter should support:

- Billing cycle start date
- Last official EB assessment date
- Next expected assessment date
- Default cycle length or bi-monthly behavior

The app should support manual correction of assessment dates.

Daily readings should be aggregated into the correct active billing cycle.

---

## 7. Solar Requirements

Solar is a first-class feature, but exact metering varies.

Current minimum:

- None
- On-grid
- Off-grid
- Cumulative solar unit reading
- Daily solar balance

Design the schema so these can be added later without breaking existing data:

- Grid import units
- Grid export units
- Net meter reading
- Inverter generation
- Battery charge/discharge
- Battery SOC
- Self-consumed solar
- Export credits/net-feed-in tariff
- Multiple inverter/meter sources

Do not assume that "Solar Unit" always equals grid export.

---

## 8. Recommended Architecture

Use a clean separation between UI, API/application services, business/domain logic, and persistence.

### Preferred stack

**Frontend**
- Flutter
- Start with Windows desktop
- Reuse the same Flutter project later for web and Android/iOS where practical

**Backend**
- Python
- FastAPI
- Pydantic
- SQLAlchemy/SQLModel or equivalent mature ORM

**Phase 1 database**
- SQLite for simple local development/testing

**Production/sync database**
- PostgreSQL

**Deployment**
- Docker / Docker Compose
- Hostinger VPS
- Reverse proxy such as Nginx or Caddy
- HTTPS in production

### Python environment

Prefer `uv` rather than `pip` for Python dependency and virtual-environment management.

### Critical architecture rule

Business logic such as balance calculation, billing-cycle determination, tariff evaluation, and validation must live outside the Flutter widgets.

The same backend/domain rules must be reusable by desktop, web, and mobile clients.

---

## 9. Suggested Repository Structure

```text
wattledger-tn/
├── CLAUDE.md
├── PRP.md
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── domain/
│   │       ├── readings.py
│   │       ├── billing_cycles.py
│   │       └── tariffs.py
│   └── tests/
├── frontend/
│   └── wattledger_flutter/
├── docs/
│   ├── decisions/
│   ├── tariff-sources/
│   └── api/
└── scripts/
```

Keep migration files when PostgreSQL/Alembic is introduced.

---

## 10. Initial Database Entities

At minimum plan for:

### Meter

- id
- meter_number
- display_name
- solar_mode
- active
- billing_cycle_reference_date
- created_at
- updated_at

### MeterReading

- id
- meter_id
- reading_date
- eb_units
- eb_balance
- solar_units
- solar_balance
- notes
- created_at
- updated_at

Unique constraint:

`(meter_id, reading_date)`

### TariffPlan

- id
- name
- provider
- consumer_category
- effective_from
- effective_to
- billing_frequency
- source_reference
- active
- created_at

### TariffSlab

- id
- tariff_plan_id
- rule_group
- from_unit
- to_unit
- rate_per_unit
- sort_order

### SubsidyRule

- id
- tariff_plan_id
- rule_name
- consumption_min
- consumption_max
- free_units
- effective_from
- effective_to

### BillingAssessment

- id
- meter_id
- period_start
- period_end
- opening_reading
- closing_reading
- consumed_units
- tariff_plan_id
- estimated_amount
- official_bill_amount
- assessed_at
- notes

Later:

### User

### Household

### UserHouseholdRole

### DeviceSession / RefreshToken

Do not add authentication tables until the authentication phase unless required by the chosen architecture.

---

## 11. Phase 1 Desktop MVP

Phase 1 must work without signup/login.

Required screens:

1. Dashboard
2. Add/Edit Meter
3. Daily Reading Entry
4. Reading History
5. Billing Cycle Summary
6. Estimated EB Bill
7. Tariff & Subsidy Settings
8. Settings / Backup

### Dashboard minimum

Show:

- Today's EB usage
- Today's solar usage
- Current billing-cycle EB usage
- Estimated current bill
- Days since last reading
- Recent usage trend
- Meter selector if multiple meters exist

### Reading entry

When user enters today's cumulative EB/Solar reading:

- Fetch the previous chronological reading
- Preview calculated balances before save
- Show clear validation errors
- Save only after validation
- Recalculate downstream balances when a historical row changes

---

## 12. Phase 2 Features

After MVP is stable:

- CSV export/import
- Local backup/restore
- Usage charts
- Daily/weekly/monthly comparisons
- Billing-cycle comparison
- Consumption targets
- High-usage alerts
- Estimated end-of-cycle consumption
- Estimated end-of-cycle bill
- Tariff version history
- Official-bill amount entry to compare estimate vs actual
- Solar savings estimate

---

## 13. Phase 3 Authentication and Synchronization

When core features are stable:

- Signup
- Login
- Password reset
- Email verification if required
- Multi-device synchronization
- PostgreSQL
- User/household ownership
- Secure API
- Access/refresh tokens or secure session model
- Conflict-handling strategy
- Backup strategy
- Rate limiting
- Audit logging for tariff/admin changes where appropriate

A user may eventually have multiple meters and possibly multiple properties.

Do not bind the data model permanently to one meter per user.

---

## 14. Security

Before internet deployment:

- No secrets in Git
- `.env` for runtime configuration
- `.env.example` with placeholders only
- Passwords hashed using a modern password hashing algorithm
- HTTPS only
- Validate all API input
- Authorization checks on every household/meter resource
- Database backups
- Least-privilege PostgreSQL account
- Docker containers should not run as root where practical
- CORS restricted to known clients/origins
- Never trust client-calculated bill/balance values

---

## 15. Testing Requirements

Use automated tests for business logic before UI polishing.

Mandatory tests:

- First reading for a meter
- Normal next-day balance
- Decimal reading
- Same-date duplicate
- Lower cumulative reading
- Missing solar reading
- Non-solar meter
- On-grid meter
- Off-grid meter
- Backdated reading insertion
- Historical edit
- Historical delete
- Billing-cycle boundary
- Exactly subsidy threshold
- One unit above subsidy threshold
- Every slab boundary
- Tariff effective-date change
- Multiple meters
- Estimated bill breakdown

Never consider the tariff engine complete without boundary tests.

---

## 16. Claude Working Rules

When implementing:

1. Read `CLAUDE.md`.
2. Read `PRP.md`.
3. Inspect existing repository code before proposing changes.
4. Do not rewrite working modules unnecessarily.
5. Work in small, verifiable increments.
6. Explain new dependencies before adding them.
7. Prefer the simplest production-suitable design.
8. Keep business logic testable without UI.
9. Add tests with each meaningful business-rule change.
10. Do not hard-code tariff/subsidy rates in UI code.
11. Do not introduce login until the MVP workflow is stable unless requested.
12. Use `uv` for Python dependency management.
13. Keep Docker support compatible with the eventual Hostinger VPS deployment.
14. Update documentation when architecture or tariff rules change.
15. If a requirement is ambiguous and materially changes the data model, record it in the PRP Open Questions section before implementation.
16. Day-to-day development happens on the `dev` branch of `https://github.com/dbala2007/WattLedger-TN`, never directly on `master`. While exiting a session, commit and push the current changes to `dev` with a commit message that accurately describes what changed.
17. Only merge `dev` into `master` when the user explicitly asks for it. At that point, open a pull request from `dev` into `master`, run a code review on the diff, post the findings as PR review comments, and let the user review and approve the merge themselves - never merge it automatically.

---

## 18. Definition of Done for a Feature

A feature is complete only when:

- Requirement is understood
- Data model impact is considered
- Business logic is implemented
- Validation is implemented
- UI/API integration works
- Automated tests cover important rules
- Error states are handled
- Existing functionality still works
- Documentation is updated when needed
