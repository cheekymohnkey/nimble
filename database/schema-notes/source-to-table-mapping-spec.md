# Source-to-Table Mapping Spec (T2)

Story: 2.5 - Persist Canonical Rules Data to SQLite  
Task: T2 - Source-to-Table Mapping Spec  
Status: complete

## Inputs and Scope

Primary inputs:

- `documentation/character-generation-requirements.md` (Story 1.5 extracted outcomes + V1 model)
- Official source books in `official_books/` (Core Rules, Heroes Core Book, Gamemaster Guide)
- Frozen schema in `database/migrations/0001_canonical_schema_freeze.sql`

This spec defines mapping for required V1 canonical domains:

- classes
- subclasses (including story-based subclasses)
- ancestries
- backgrounds
- skills
- languages
- features/abilities
- spells

Related static catalogs that support these domains (`ruleset`, `boon`, `equipment_item`) are included where needed for referential completeness.

## Global Mapping Rules

### G1) Source record model

T3/T4 seed inputs should use a normalized extraction format with explicit source provenance per row.

Required provenance fields on extraction records:

- `source_book` (`core_rules`, `heroes_core`, `gamemaster_guide`)
- `source_page_ref` (page or range text)
- `source_section` (free text heading)

### G2) Ruleset resolution

All ruleset-scoped rows resolve `ruleset_id` via natural key `(ruleset.name, ruleset.version)`.

Default V1 ruleset row for initial load:

- `name = Nimble 5e`
- `version = v1`
- `source_book = Core Rules + Heroes Core Book + Gamemaster Guide`

### G3) Deterministic ordering

For stable clean rebuilds, seed pipeline inserts rows sorted by natural key order before ID lookups.

### G4) Conflict strategy

Canonical strategy for repeatable seed:

- `INSERT ... ON CONFLICT DO UPDATE` on each table natural key.
- Update descriptive/mutable text columns (`description`, JSON blobs, costs, flags).
- Never rewrite foreign key identity relationships to different parents during upsert; reject as mapping error.

### G5) Nullability and strictness

- If column is nullable in schema and source value is unavailable, write `NULL`.
- If column is required and source value is unavailable, fail seed with explicit extraction error.
- For enum/check columns, source normalization must happen pre-insert; invalid enum values are hard errors.

## Domain Mapping

## D0) Ruleset bootstrap

Target table: `ruleset`

| Source field | Target column | Transform |
| --- | --- | --- |
| `ruleset_name` | `name` | direct |
| `ruleset_version` | `version` | direct |
| `source_book` | `source_book` | join distinct book names if multi-source |
| `source_page_ref` | `source_page_ref` | direct |

Natural key: `(name, version)`  
Conflict strategy: update `source_book`, `source_page_ref` on conflict.

Nullable/deferred:

- `source_book`, `source_page_ref` may be `NULL` if provenance unavailable.

## D1) Classes

Primary source:

- `Classes` section and class detail sections in requirements/book extracts.

Target table: `character_class`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup `ruleset.id` by `(name, version)` |
| `class_name` | `name` | trim, title-preserving canonical text |
| `class_description` | `description` | direct |
| `hit_die` | `hit_die` | integer parse |
| `starting_hp` | `starting_hp` | integer parse |
| `key_stat_1` | `key_stat_1` | normalize to `STR|DEX|INT|WIL` |
| `key_stat_2` | `key_stat_2` | normalize to `STR|DEX|INT|WIL` |
| `save_adv_stat` | `save_adv_stat` | normalize to `STR|DEX|INT|WIL` |
| `save_disadv_stat` | `save_disadv_stat` | normalize to `STR|DEX|INT|WIL` |
| `armor_proficiencies` | `armor_proficiencies_json` | JSON encode ordered list |
| `weapon_proficiencies` | `weapon_proficiencies_json` | JSON encode ordered list |
| `starting_gear` | `starting_gear_json` | JSON encode ordered object/list |

Natural key: `(ruleset_id, name)`  
Conflict strategy:

- Upsert by natural key.
- Update descriptive and JSON payload columns.
- Reject update if enum-normalized stats violate table checks.

Nullable/deferred:

- `description`, `armor_proficiencies_json`, `weapon_proficiencies_json`, `starting_gear_json` may be `NULL` if extraction is incomplete.
- `hit_die`, `starting_hp`, key/save stats are required and non-null.

## D2) Subclasses

Primary source:

- `Standard subclass pairs` and `Story-based subclasses` in requirements/book extracts.

Target table: `subclass`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup from D0 |
| `parent_class_name` | `class_id` | lookup `character_class.id` by `(ruleset_id, class_name)` |
| `subclass_name` | `name` | direct |
| `is_story_based` | `is_story_based` | bool to `0/1` |
| `subclass_description` | `description` | direct |

Natural key: `(class_id, name)`  
Conflict strategy:

- Upsert by `(class_id, name)`.
- Update `is_story_based`, `description`.
- Reject records if `parent_class_name` cannot be resolved.

Nullable/deferred:

- `description` may be `NULL`.
- `is_story_based` defaults to `0` if omitted.

## D3) Ancestries

Primary source:

- `Ancestries (from Core Rules)` and extracted ancestry detail sections.

Target tables: `ancestry`, `ancestry_trait`

### D3a) `ancestry`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup from D0 |
| `ancestry_name` | `name` | direct |
| `size_category` | `size_category` | normalize to enum (`tiny/small/medium/large/varies/other`) |
| `ancestry_description` | `description` | direct |

Natural key: `(ruleset_id, name)`  
Conflict strategy: upsert and update `size_category`, `description`.

Nullable/deferred:

- `size_category` may be `NULL` when not explicit in source.
- `description` may be `NULL`.

### D3b) `ancestry_trait`

| Source field | Target column | Transform |
| --- | --- | --- |
| `ancestry_name` | `ancestry_id` | lookup `ancestry.id` by `(ruleset_id, ancestry_name)` |
| `trait_name` | `name` | direct |
| `trait_description` | `description` | direct |
| `trait_effects` | `effects_json` | JSON encode normalized effects |

Natural key: `(ancestry_id, name)`  
Conflict strategy: upsert and update `description`, `effects_json`.

Nullable/deferred:

- `description`, `effects_json` may be `NULL`.
- Freeform rules text can be stored in `description` until structured effects are finalized.

## D4) Backgrounds

Primary source:

- Background sections and extracted background trait details.

Target tables: `background`, `background_trait`

### D4a) `background`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup from D0 |
| `background_name` | `name` | direct |
| `background_description` | `description` | direct |

Natural key: `(ruleset_id, name)`  
Conflict strategy: upsert and update `description`.

Nullable/deferred:

- `description` may be `NULL`.

### D4b) `background_trait`

| Source field | Target column | Transform |
| --- | --- | --- |
| `background_name` | `background_id` | lookup `background.id` by `(ruleset_id, background_name)` |
| `trait_name` | `name` | direct |
| `trait_description` | `description` | direct |
| `trait_prereq` | `prereq_json` | JSON encode prerequisite object |
| `trait_effects` | `effects_json` | JSON encode effects object |

Natural key: `(background_id, name)`  
Conflict strategy: upsert and update `description`, `prereq_json`, `effects_json`.

Nullable/deferred:

- `description`, `prereq_json`, `effects_json` may be `NULL`.
- Complex conditional prerequisites may remain narrative-only in `description` until structured rule parser exists.

## D5) Skills

Primary source:

- Fixed skill catalog in requirements:
  - `Might`
  - `Finesse`, `Stealth`
  - `Arcana`, `Examination`, `Lore`
  - `Influence`, `Insight`, `Naturecraft`, `Perception`

Target table: `skill`

| Source field | Target column | Transform |
| --- | --- | --- |
| `skill_name` | `name` | direct |
| `governing_stat` | `governing_stat` | normalize to `STR|DEX|INT|WIL` |
| `skill_description` | `description` | direct |

Natural key: `name`  
Conflict strategy: upsert by `name`, update `governing_stat`, `description`.

Nullable/deferred:

- `description` may be `NULL`.

## D6) Languages

Primary source:

- Fixed language catalog in requirements:
  - Common, Dwarvish, Elvish, Goblin, Infernal, Thieves' Cant, Celestial, Draconic, Primordial, Deep Speak

Target table: `language`

| Source field | Target column | Transform |
| --- | --- | --- |
| `language_name` | `name` | direct |
| `language_description` | `description` | direct |

Natural key: `name`  
Conflict strategy: upsert by `name`, update `description`.

Nullable/deferred:

- `description` may be `NULL`.

## D7) Features/Abilities

Primary source:

- Class progression features and ability-choice lists in class sections.
- Ability pools listed in requirements (for example Savage Arsenal, Underhanded Abilities, Spellshaper abilities, etc.).

Target tables:

- `class_level_feature`
- `feature_choice_group`
- `feature_choice_option`

### D7a) `class_level_feature`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup from D0 |
| `class_name` | `class_id` | lookup from `character_class` |
| `subclass_name` (optional) | `subclass_id` | lookup from `subclass` when present, else `NULL` |
| `level` | `level` | integer parse 1..20 |
| `feature_name` | `name` | direct |
| `feature_description` | `description` | direct |
| `feature_type` | `feature_type` | normalize to allowed enum |
| `display_order` | `display_order` | integer, default 0 |

Natural keys (scope-aware):

- class-wide feature: `(ruleset_id, class_id, level, name)` where `subclass_id IS NULL`
- subclass feature: `(ruleset_id, class_id, subclass_id, level, name)` where `subclass_id IS NOT NULL`

Conflict strategy:

- Upsert using matching partial-unique key by scope.
- Update `description`, `feature_type`, `display_order`.
- Reject if subclass does not belong to resolved class.

Nullable/deferred:

- `subclass_id` nullable for class-wide progression features.
- `description` may be `NULL`.
- `feature_type` normalization fallback:
  - use `choice_grant` for rows that create choice groups
  - use `other` only when no specific enum fits

### D7b) `feature_choice_group`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup from D0 |
| `class_name` | `class_id` | lookup from `character_class` |
| `subclass_name` (optional) | `subclass_id` | lookup from `subclass` when present |
| `group_name` | `name` | direct |
| `max_choices` | `max_choices` | integer parse (>0) |
| `respec_rule` | `respec_rule` | normalize to enum, default `never` |
| `group_description` | `description` | direct |

Natural keys (scope-aware):

- class-wide group: `(ruleset_id, class_id, name)` where `subclass_id IS NULL`
- subclass group: `(ruleset_id, class_id, subclass_id, name)` where `subclass_id IS NOT NULL`

Conflict strategy: upsert by scoped key; update `max_choices`, `respec_rule`, `description`.

Nullable/deferred:

- `subclass_id` nullable.
- `description` may be `NULL`.
- `max_choices` required; missing value is extraction error.

### D7c) `feature_choice_option`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved group key | `choice_group_id` | lookup from `feature_choice_group` |
| `option_name` | `name` | direct |
| `option_description` | `description` | direct |
| `option_prereq` | `prereq_json` | JSON encode prerequisite object |
| `option_effects` | `effects_json` | JSON encode effects object |
| `display_order` | `display_order` | integer default 0 |

Natural key: `(choice_group_id, name)`  
Conflict strategy: upsert by natural key; update descriptive JSON fields and ordering.

Nullable/deferred:

- `description`, `prereq_json`, `effects_json` may be `NULL`.
- Structured prerequisite/effect schemas are deferred; V1 can store minimally structured JSON.

## D8) Spells

Primary source:

- Spell lists and spell definitions extracted from class/spell sections in Core/Heroes books.

Target table: `spell`

| Source field | Target column | Transform |
| --- | --- | --- |
| resolved ruleset | `ruleset_id` | lookup from D0 |
| `spell_name` | `name` | direct |
| `school` | `school` | direct normalized text |
| `tier` | `tier` | integer parse (`0` allowed for cantrip-like entries) |
| `is_cantrip` | `is_cantrip` | bool to `0/1` |
| `action_cost` | `action_cost` | direct |
| `mana_cost` | `mana_cost` | integer parse |
| `spell_description` | `description` | direct |

Natural key: `(ruleset_id, name)`  
Conflict strategy: upsert and update all non-key payload columns.

Nullable/deferred:

- `school`, `action_cost`, `mana_cost`, `description` may be `NULL` if not present in extracted text.
- Class-to-spell learnability mapping is deferred in V1 schema (no join table yet).

## Supporting Catalogs (Related but not core T2 deliverable)

## S1) Boons

Target table: `boon`  
Natural key: `(ruleset_id, name)`

Mapping fields:

- `name`, `boon_tier`, `description`, `effects_json`.

Deferred details:

- Fine-grained boon stacking/expiry policy remains service-layer concern.

## S2) Equipment

Target table: `equipment_item`  
Natural key: `(ruleset_id, name)`

Mapping fields:

- `name`, `category`, `slot_cost`, `armor_value`, `properties_json`.

Deferred details:

- Complex grouped-slot packing semantics are deferred to rules engine/service layer.

## Validation/Load Preconditions for T3

Seed pipeline must fail fast when any of these are true:

- subclass source references unknown class
- feature source references unknown class or subclass
- required class fields (`hit_die`, `starting_hp`, key/save stats) missing
- required feature group fields (`max_choices`) missing
- spell `tier` missing or non-numeric

## Required Coverage Targets for T4/T5

These targets become baseline checks once data is loaded:

- classes: 11
- story-based subclasses: 4 (Oathbreaker, Spellblade, Reaver, Beastmaster)
- skills: 10
- languages: 10
- subclasses, ancestries, backgrounds, spells, features: non-zero and source-traceable

## Deferred Fields and Domains (Explicit)

Deferred structured modeling in V1 (stored as nullable text/JSON or not represented yet):

- deeply structured mechanical effect grammar for traits/features/spells
- class-to-spell association matrix (requires additional relation table)
- campaign-specific policy metadata for story-triggered subclass swaps

These deferrals are by design and will be carried into T4/T6 documentation.
