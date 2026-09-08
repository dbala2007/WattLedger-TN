# 0001 - Use UUID string primary keys, not auto-increment integers

**Status:** Decided (Phase 0/1 backend skeleton)

## Context

PRP.md section 10 (Data Migration Strategy) requires that entity IDs be
"portable" before cloud synchronization is introduced, since multiple
offline devices will eventually need to create records that later merge
into one shared database (PRP.md section 13, Phase 4/5).

## Decision

`Meter.id` and `MeterReading.id` are randomly-generated UUID strings
(`uuid.uuid4()`), not database auto-increment integers.

## Consequences

- No ID collisions when two devices create records offline and sync later.
- No painful primary-key-type migration when moving from SQLite to
  PostgreSQL for synchronization.
- IDs are slightly larger (36-character strings vs. small integers), which
  is irrelevant at household data volumes (NFR-004).
