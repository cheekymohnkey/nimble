# Canonical Schema Freeze (T1)

Story: 2.5 - Persist Canonical Rules Data to SQLite  
Task: T1 - Canonical Schema Freeze  
Status: frozen

## Scope frozen in this migration

Migration: `database/migrations/0001_canonical_schema_freeze.sql`

The canonical (static/reference) V1 rules domains are frozen as:

- `ruleset`
- `character_class`
- `subclass`
- `class_level_feature`
- `feature_choice_group`
- `feature_choice_option`
- `ancestry`
- `ancestry_trait`
- `background`
- `background_trait`
- `skill`
- `language`
- `spell`
- `boon`
- `equipment_item`

This covers Story 2.5 canonical lookup requirements for class/subclass/ancestry/background/skills/languages/features/spells and related static catalogs needed by V1 character generation.

## Key constraints frozen

- Required FK paths from child catalogs back to their parent catalogs.
- `UNIQUE` keys on natural lookup identities (for example `(ruleset_id, name)` where ruleset-scoped).
- Story-subclass metadata: `subclass.is_story_based` constrained to boolean (`0`/`1`).
- Stat key checks constrained to `STR`, `DEX`, `INT`, `WIL` where applicable.
- Level bounds on class features constrained to `1..20`.
- Tier/enumeration constraints on:
  - `class_level_feature.feature_type`
  - `feature_choice_group.respec_rule`
  - `boon.boon_tier`
- Non-negative numeric constraints for costs and pools where applicable (`mana_cost`, `slot_cost`, etc.).

## Compatibility rules encoded in schema

- Subclass rows must reference a valid class in the same ruleset.
- Class-level feature and feature-choice rows can be class-wide or subclass-specific.
- Subclass-scoped rows use composite FK linkage so subclass references cannot drift across class/ruleset boundaries.

## Out of scope for T1

- Mutable character-state tables (`character`, `character_skill`, `character_subclass_history`, etc.).
- Seed content and source-to-table mappings (T2/T3/T4).
- Coverage/integrity test suite implementation (T5).

## Gate A check command

```bash
sqlite3 /tmp/nimble_t1_gate_a.sqlite < database/migrations/0001_canonical_schema_freeze.sql
```

Success condition: command exits with no SQL errors on an empty DB.
