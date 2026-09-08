# WattLedger TN - Backend

FastAPI + SQLModel backend. See the [project README](../README.md) and
[`PRP.md`](../PRP.md) / [`CLAUDE.md`](../CLAUDE.md) at the repository root
for product context and working rules.

## Setup

```bash
uv sync
```

## Run tests

```bash
uv run pytest -v
```

## Run the API locally

```bash
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API docs.

## Folder structure

| Folder | Purpose |
|---|---|
| `app/api/` | FastAPI routers (HTTP request/response only) |
| `app/services/` | Orchestrates a use case: fetch data, call domain rules, save |
| `app/domain/` | Pure business rules - no database or HTTP dependency |
| `app/repositories/` | Database queries (SQLModel/SQLAlchemy), no business rules |
| `app/models/` | SQLModel table definitions |
| `app/schemas/` | Pydantic request/response shapes for the API |
| `app/core/` | Configuration and logging setup |
| `app/db/` | Database engine/session setup |
| `tests/` | Automated tests (pytest) |
| `scripts/` | One-off dev scripts, e.g. seeding an example tariff plan |

## Example: create a meter and two readings

```bash
curl -X POST http://127.0.0.1:8000/meters \
  -H "Content-Type: application/json" \
  -d '{"meter_number": "EB-1234", "solar_mode": "ON_GRID"}'

curl -X POST http://127.0.0.1:8000/meters/<meter_id>/readings \
  -H "Content-Type: application/json" \
  -d '{"reading_date": "2026-05-01", "eb_units": 12500.4, "solar_units": 4200.0}'

curl -X POST http://127.0.0.1:8000/meters/<meter_id>/readings \
  -H "Content-Type: application/json" \
  -d '{"reading_date": "2026-05-02", "eb_units": 12508.9, "solar_units": 4207.5}'

curl http://127.0.0.1:8000/meters/<meter_id>/readings
```

The second reading's response includes `eb_balance: 8.500` and
`solar_balance: 7.500`, calculated automatically - matching the example in
`PRP.md` section 2.

## Example: billing cycle and bill estimate

First seed an example tariff plan (placeholder rates - see the warning in
`scripts/seed_dev_tariff.py`):

```bash
uv run python scripts/seed_dev_tariff.py
```

Then, using a `<meter_id>` created with a `billing_cycle_reference_date` and
at least one EB reading:

```bash
curl http://127.0.0.1:8000/meters/<meter_id>/billing-cycle/current
curl http://127.0.0.1:8000/meters/<meter_id>/bill-estimate
```

`bill-estimate` returns the full breakdown required by `PRP.md` FR-007:
total cycle units, free units applied, chargeable units, every slab charged
(with its rate and amount), the fixed charge, the total, and which tariff
plan/version was used - never just a final number.

### Tariff plan configuration

`POST /tariffs` creates a new effective-dated tariff plan together with its
subsidy rules and slabs in one request (see `app/schemas/tariff.py` for the
shape). Existing tariff plans are never edited in place - add a new one with
a later `effective_from` instead, so historical bills keep using the
version that was actually in force at the time (`PRP.md` section 5).
