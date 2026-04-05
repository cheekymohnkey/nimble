# Story 2.5 Execution Checklist

## Story

- Story: Persist Canonical Rules Data to SQLite
- Epic: `agile_process/epic-character-generator-requirements.md`
- Status: ready for review
- Scope: V1 canonical rules domains required for character generation and persistence

## Objective

Seed canonical Nimble character rules data into SQLite so the generator resolves class/subclass/ancestry/background/skills/languages/features/spells from database tables rather than hardcoded constants.

## Owners

- Delivery Owner: Team
- Schema/Migrations: Backend
- Extraction and Transformation: Data/Backend
- Seed Pipeline and Tooling: Backend
- Verification and QA: Backend + QA
- Requirements Traceability: Product/Design

## Work Sequence

1. Finalize canonical table list and migration plan.
2. Build extraction mapping spec from source definitions to canonical tables.
3. Implement seed pipeline (clean rebuild and/or idempotent upsert path).
4. Seed baseline dataset from documented official definitions.
5. Add integrity, compatibility, and coverage checks.
6. Run clean-database verification and capture outputs.
7. Document deferred domains and publish runbook.

## Task Checklist

### T1 - Canonical Schema Freeze

- Owner: Schema/Migrations
- Status: done (2026-04-05)
- Inputs: `documentation/character-generation-requirements.md` (data model + V1 scope)
- Actions:
  - Confirm canonical lookup tables for V1 domains.
  - Define key constraints (FK, unique keys, required columns).
  - Create or update migration(s).
- Deliverables:
  - Migration files committed.
  - Schema notes for canonical tables.
- Artifacts:
  - `database/migrations/0001_canonical_schema_freeze.sql`
  - `database/schema-notes/canonical-schema-freeze.md`
- Verification:
  - `sqlite3 -bail /tmp/nimble_t1_gate_a.sqlite < database/migrations/0001_canonical_schema_freeze.sql`
  - `SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';` => `15`
  - `PRAGMA foreign_key_check;` => no rows
- Done Criteria:
  - SQLite DB applies migrations from empty state with no errors.

### T2 - Source-to-Table Mapping Spec

- Owner: Extraction and Transformation
- Status: done (2026-04-05)
- Inputs: official extracted definitions + story scope
- Actions:
  - Define exact mapping fields for classes, subclasses, ancestries, backgrounds, skills, languages, features/abilities, spells.
  - Define stable natural keys and conflict strategy.
  - Identify nullable fields and deferred fields.
- Deliverables:
  - Mapping spec document (table-by-table).
- Artifacts:
  - `database/schema-notes/source-to-table-mapping-spec.md`
- Verification:
  - Includes explicit field-level mapping paths for classes, subclasses, ancestries, backgrounds, skills, languages, features/abilities, and spells.
  - Includes stable natural keys per target table and upsert conflict strategy.
  - Includes nullable/deferred field treatment and T3 preconditions.
- Done Criteria:
  - Every required V1 domain has an explicit mapping path.

### T3 - Seed Pipeline Implementation

- Owner: Seed Pipeline and Tooling
- Status: done (2026-04-05)
- Inputs: T1 schema, T2 mapping
- Actions:
  - Build seed command/workflow.
  - Support clean rebuild path and deterministic ordering.
  - Add basic logging and failure reporting.
- Deliverables:
  - Runnable seed command(s).
  - Seed source files/versioned inputs.
- Artifacts:
  - `scripts/seed_canonical_rules.py`
  - `database/seed_data/v1/`
- Verification:
  - `python3 scripts/seed_canonical_rules.py --db /tmp/nimble_t3.sqlite --rebuild --verbose`
  - Result: migration applied and seed completed (`ruleset` inserted=1, `skill` inserted=10, `language` inserted=10).
  - `sqlite3 /tmp/nimble_t3.sqlite "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"` => `15`
  - `sqlite3 /tmp/nimble_t3.sqlite "SELECT count(*) FROM ruleset; SELECT count(*) FROM skill; SELECT count(*) FROM language;"` => `1`, `10`, `10`
  - `sqlite3 /tmp/nimble_t3.sqlite "PRAGMA foreign_key_check;"` => no rows
  - Idempotence check: `python3 scripts/seed_canonical_rules.py --db /tmp/nimble_t3.sqlite --verbose` updates existing rows without duplicate inserts.
- Done Criteria:
  - Seed command completes successfully on empty DB.

### T4 - Canonical Dataset Load

- Owner: Extraction and Transformation
- Status: done (2026-04-05)
- Inputs: T3 pipeline + official definitions
- Actions:
  - Prepare and load initial canonical dataset.
  - Include story-based subclasses with explicit metadata/flag.
  - Record any intentionally deferred domains.
- Deliverables:
  - Seeded SQLite dataset.
  - Deferred-domain list.
- Artifacts:
  - `database/seed_data/v1/*.json`
  - `database/seed_data/v1/README.md`
- Verification:
  - `python3 scripts/seed_canonical_rules.py --db /tmp/nimble_t4.sqlite --rebuild --verbose`
  - Result: migration applied and canonical domain seed completed.
  - `sqlite3 /tmp/nimble_t4.sqlite "SELECT count(*) FROM character_class; SELECT count(*) FROM subclass; SELECT count(*) FROM subclass WHERE is_story_based=1; SELECT count(*) FROM ancestry; SELECT count(*) FROM background; SELECT count(*) FROM class_level_feature; SELECT count(*) FROM spell;"` => `11`, `26`, `4`, `24`, `10`, `122`, `12`
  - `sqlite3 /tmp/nimble_t4.sqlite "PRAGMA foreign_key_check;"` => no rows
  - Idempotence check: `python3 scripts/seed_canonical_rules.py --db /tmp/nimble_t4.sqlite --verbose` updates existing rows without duplicate inserts.
- Done Criteria:
  - V1 required domain rows are present and queryable.

### T5 - Integrity and Coverage Validation

- Owner: Verification and QA
- Status: done (2026-04-05)
- Inputs: seeded DB
- Actions:
  - Validate FK and uniqueness constraints.
  - Validate class/subclass compatibility rules.
  - Validate representative coverage counts per domain.
  - Validate deterministic seed outcome on clean re-run.
- Deliverables:
  - Validation report/check output.
- Artifacts:
  - `scripts/validate_canonical_rules.py`
- Verification:
  - `python3 scripts/seed_canonical_rules.py --db /tmp/nimble_t5_a.sqlite --rebuild --verbose`
  - `python3 scripts/seed_canonical_rules.py --db /tmp/nimble_t5_b.sqlite --rebuild --verbose`
  - `python3 scripts/validate_canonical_rules.py --db /tmp/nimble_t5_a.sqlite --compare-db /tmp/nimble_t5_b.sqlite`
  - Result: PASS (integrity + FK + uniqueness + class/subclass compatibility + coverage thresholds + deterministic equivalence).
  - Coverage output (selected): `character_class=11`, `subclass=26`, `story-based subclasses=4`, `skill=10`, `language=10`, `ancestry=24`, `background=10`, `class_level_feature=122`, `spell=12`.
- Done Criteria:
  - All hard checks pass.
  - Coverage checks meet V1 thresholds.

### T6 - Runbook and Traceability

- Owner: Requirements Traceability
- Status: done (2026-04-05)
- Inputs: T1-T5 outputs
- Actions:
  - Document how to run migrations + seed + verification locally.
  - Link seeded domains back to requirements and Story 2.5 acceptance conditions.
  - Document deferred domains with rationale.
- Deliverables:
  - Story 2.5 runbook/checklist completion note.
- Artifacts:
  - `agile_process/story-2.5-runbook.md`
- Verification:
  - Runbook contains executable local commands for migration + seed + verification.
  - Traceability links acceptance conditions to schema, seed data, and validation outputs.
  - Deferred domains are explicitly listed with rationale.
- Done Criteria:
  - New teammate can run setup and verify with documented commands only.

## Verification Gates

- Gate A (Schema Ready): complete (2026-04-05).
- Gate B (Seed Ready): complete (2026-04-05).
- Gate C (Data Ready): complete (2026-04-05).
- Gate D (Release to Next Story): complete (2026-04-05).

## Acceptance Conditions Traceability

1. Runtime resolution from SQLite lookup tables: validated in T4/T5.
2. Story-based subclass representation: validated in T4/T5.
3. Deferred domains explicitly listed: documented in T4/T6.

## Risks and Mitigations

- Risk: schema drift while seeding.
  - Mitigation: freeze schema at Gate A before pipeline finalization.
- Risk: ambiguous source mapping.
  - Mitigation: explicit mapping spec in T2 with unresolved-field log.
- Risk: non-deterministic seed outputs.
  - Mitigation: stable ordering and repeat clean-run checks in T5.

## Completion Definition

Story 2.5 is complete when T1 through T6 are done and Gate D passes.
