# Story 2.5 Runbook and Traceability

Story: Persist Canonical Rules Data to SQLite  
Status: ready for review (T1-T6 complete as of 2026-04-05)

## Purpose

This runbook documents the exact local commands to migrate, seed, and validate canonical rules data for Story 2.5, plus traceability to Story 2.5 acceptance conditions.

## Preconditions

- Run commands from repository root: `nimble/`
- `python3` available on PATH
- `sqlite3` available on PATH (only needed for optional manual spot checks)

## Local Setup and Verification Commands

### 1) Build canonical DB from scratch

```bash
python3 scripts/seed_canonical_rules.py --db /tmp/nimble_story25.sqlite --rebuild --verbose
```

Expected result:

- Migration applies successfully.
- Seed completes with non-zero rows for required V1 domains.

### 2) Validate integrity + coverage (single DB)

```bash
python3 scripts/validate_canonical_rules.py --db /tmp/nimble_story25.sqlite
```

Expected result:

- `PASS canonical rules validation`
- Coverage includes at least:
  - `character_class=11`
  - `subclass=26`
  - `skill=10`
  - `language=10`
  - `ancestry=24`
  - `background=10`
  - `class_level_feature=122`
  - `spell=12`

### 3) Validate deterministic clean rebuild behavior

```bash
python3 scripts/seed_canonical_rules.py --db /tmp/nimble_story25_a.sqlite --rebuild --verbose
python3 scripts/seed_canonical_rules.py --db /tmp/nimble_story25_b.sqlite --rebuild --verbose
python3 scripts/validate_canonical_rules.py --db /tmp/nimble_story25_a.sqlite --compare-db /tmp/nimble_story25_b.sqlite
```

Expected result:

- Validation pass for integrity/coverage.
- `PASS deterministic equivalence vs /tmp/nimble_story25_b.sqlite`

### 4) Optional SQL spot checks

```bash
sqlite3 /tmp/nimble_story25.sqlite "PRAGMA foreign_key_check;"
sqlite3 /tmp/nimble_story25.sqlite "SELECT count(*) FROM subclass WHERE is_story_based=1;"
sqlite3 /tmp/nimble_story25.sqlite "SELECT count(*) FROM character_class; SELECT count(*) FROM skill; SELECT count(*) FROM language;"
```

Expected values:

- FK check returns no rows.
- Story-based subclasses count: `4`
- Class/skill/language counts: `11`, `10`, `10`

## Acceptance Condition Traceability

1. Runtime resolution from SQLite lookup tables.
- Evidence:
  - `database/migrations/0001_canonical_schema_freeze.sql`
  - Seeded canonical catalogs in `database/seed_data/v1/*.json`
  - Seed execution and counts in `agile_process/story-2.5-execution-checklist.md`
  - Validation output from `scripts/validate_canonical_rules.py`

2. Story-based subclass representation.
- Evidence:
  - `subclass.is_story_based` schema constraint in `database/migrations/0001_canonical_schema_freeze.sql`
  - Story-based rows in `database/seed_data/v1/subclasses.json`:
    - `Oathbreaker`
    - `Spellblade`
    - `Reaver`
    - `Beastmaster`
  - Validation assertion in `scripts/validate_canonical_rules.py`

3. Deferred domains explicitly listed.
- Evidence:
  - `database/schema-notes/source-to-table-mapping-spec.md` (Deferred Fields and Domains section)
  - `database/seed_data/v1/README.md` (T4 deferred domains/fields)
  - This runbook section below

## Deferred Domains and Rationale (V1)

- Structured effect grammar for traits/features/spells:
  - Kept as minimally structured JSON payloads in V1 (`effects_json`).
- Class-to-spell learnability matrix:
  - Deferred pending an additional relation table in schema.
- Campaign-policy metadata for story-triggered subclass swaps:
  - Deferred to service-layer/domain-policy logic.

## Key Artifacts

- Migration: `database/migrations/0001_canonical_schema_freeze.sql`
- Mapping spec: `database/schema-notes/source-to-table-mapping-spec.md`
- Seed data: `database/seed_data/v1/`
- Seeder: `scripts/seed_canonical_rules.py`
- Validator: `scripts/validate_canonical_rules.py`
- Execution checklist: `agile_process/story-2.5-execution-checklist.md`
