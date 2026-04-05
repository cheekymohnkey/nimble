# Character Generator Requirements and Data Model

## Review Scope

Reviewed and cross-checked:

- `documentation/technical-approach.md`
- `agile_process/epic-character-generator-requirements.md`
- `official_books/Nimble 5e TTRPG Core Rules ...pdf`
- `official_books/Nimble 5e TTRPG Heroes Core Book ...pdf`
- `official_books/Nimble 5e TTRPG Gamemaster Guide ...pdf`

## What We Have Learned (High Level)

### 1. Character creation order is explicit

Core Rules define:

1. Choose class (primary mechanical identity)
2. Choose ancestry + background (plus optional adventuring motivation)
3. Fill sheet details (stats, skills, resources, equipment, languages)

### 2. Character identity is class-first and progression-heavy

Each class defines at minimum:

- key stats (2)
- hit die
- starting HP
- save profile (one advantaged, one disadvantaged)
- armor/weapon proficiencies
- starting gear
- level progression from 1 to 20

Progression pattern seen across classes:

- subclass choice at level 3
- subclass feature milestones at levels 7, 11, 15
- regular key/secondary stat increases
- level 19 Epic Boon
- level 20 capstone

### 3. Core sheet model is broader than just stats

Required persistent fields from Core Rules sheet:

- identity: name, ancestry, class, level, height, weight
- base stats: STR, DEX, INT, WIL
- saves: one advantaged, one disadvantaged, two neutral
- skill values (base from stats + allocated points)
- HP, hit die size, hit dice count
- wounds (default cap 6 unless modified)
- initiative, speed
- inventory slots (`10 + STR`) and slot usage
- equipment and money
- languages (Common by default + INT-based additions)
- "other abilities" from class/subclass/ancestry/background

### 4. Skills and language systems are fixed catalogs

Skills in Core Rules map to one governing stat each:

- STR: Might
- DEX: Finesse, Stealth
- INT: Arcana, Examination, Lore
- WIL: Influence, Insight, Naturecraft, Perception

Languages listed in Core Rules:

- Common, Dwarvish, Elvish, Goblin, Infernal, Thieves' Cant, Celestial, Draconic, Primordial, Deep Speak

### 5. Ancestry and background are feature-bearing entities

Ancestries provide stat/effect modifiers and often conditional language grants.
Backgrounds provide traits, sometimes prerequisites, and can alter abilities/resources.

Core Rules include:

- common ancestries
- exotic ancestries
- flexible flavor guidance ("flavor is free")
- selectable backgrounds with mechanical effects
- optional adventuring motivation prompts

### 6. Classes are built on selectable ability pools

Classes repeatedly grant choices from ability lists, for example:

- Berserker: Savage Arsenal
- Cheat: Underhanded Abilities
- Commander: Commands / Combat abilities / Weapon Mastery options
- Hunter: Thrill of the Hunt abilities
- Mage: Spellshaper abilities
- Oathsworn: Sacred Decrees
- Shadowmancer: Lesser/Greater Invocations
- Shepherd: Sacred Graces
- Songweaver: Lyrical Weaponry
- Stormshifter: Chimeric Boons
- Zephyr: Martial Arts abilities

This means persistence must store not only class + subclass, but every selected option and when it was chosen.

### 7. Several classes are spell/resource classes

Books define class-specific resource systems:

- mana pools with class formulas
- per-encounter charges
- per-safe-rest uses
- temporary combat-only resources
- custom class pools (Fury Dice, Combat Dice, Judgement Dice, TotH charges, Beastshift charges, etc.)

We need a generic resource model, not hardcoded HP-only tracking.

### 8. Inventory is slot-based, not pure weight-based

Core Rules inventory is by slot count with item size/grouping semantics:

- one-slot vs two-slot items
- grouped small item bundles
- equipped/worn/held/carried state matters

### 9. Gamemaster Guide adds persistent/temporary buffs

Character persistence should account for boons/effects:

- Minor/Major/Epic Boons
- temporary lodging boons (expire on next safe rest)
- Epic Boons referenced by class level 19 progression

These are character modifiers that can be permanent, temporary, or event-scoped.

### 10. Story-based subclass replacement exists

Heroes book includes story-driven subclass replacements (Oathbreaker, Spellblade, Reaver, Beastmaster), chosen mid-campaign by GM discretion.

Data model must support subclass replacement history, not assume subclass is immutable after level 3.

## Static Catalogs To Seed

### Classes

- Berserker
- The Cheat
- Commander
- Hunter
- Mage
- Oathsworn
- Shadowmancer
- Shepherd
- Songweaver
- Stormshifter
- Zephyr

### Standard subclass pairs (by class)

- Berserker: Path of the Mountainheart, Path of the Red Mist
- The Cheat: Tools of the Silent Blade, Tools of the Scoundrel
- Commander: Champion of the Bulwark, Champion of the Vanguard
- Hunter: Keeper of the Shadowpath, Keeper of the Wild Heart
- Mage: Invoker of Control, Invoker of Chaos
- Oathsworn: Oath of Vengeance, Oath of Refuge
- Shadowmancer: Pact of the Red Dragon, Pact of the Abyssal Depths
- Shepherd: Luminary of Mercy, Luminary of Malice
- Songweaver: Herald of Snark, Herald of Courage
- Stormshifter: Circle of Sky & Storm, Circle of Fang & Claw
- Zephyr: Way of Pain, Way of Flame

### Story-based subclasses

- Oathsworn: Oathbreaker
- Commander: Spellblade
- Shadowmancer: Reaver
- Hunter: Beastmaster

### Ancestries (from Core Rules)

- Common: Human, Dwarf, Elf, Halfling, Gnome
- Exotic examples: Bunbun, Dragonborn, Fiendkin, Goblin, Kobold, Orc, Birdfolk, Celestial, Changeling, Crystalborn, Dryad/Shroomling, Half-Giant, Minotaur/Beastfolk, Oozeling/Construct, Planarbeing, Ratfolk, Stoatling, Turtlefolk, Wyrdling

## Proposed Data Model (Initial)

Design principle: separate immutable game definitions from mutable character state.

### A) Rules definition tables (static/reference)

- `ruleset`
  - `id`, `name`, `version`, `source_book`, `source_page_ref`
- `character_class`
  - `id`, `ruleset_id`, `name`, `description`, `hit_die`, `starting_hp`
  - `key_stat_1`, `key_stat_2`, `save_adv_stat`, `save_disadv_stat`
  - `armor_proficiencies_json`, `weapon_proficiencies_json`, `starting_gear_json`
- `subclass`
  - `id`, `ruleset_id`, `class_id`, `name`, `is_story_based`, `description`
- `class_level_feature`
  - `id`, `ruleset_id`, `class_id`, `subclass_id_nullable`, `level`, `name`, `description`
  - `feature_type` (`auto`, `choice_grant`, `resource_change`, `stat_increase`, etc.)
- `feature_choice_group`
  - `id`, `ruleset_id`, `class_id`, `subclass_id_nullable`, `name`, `max_choices`, `respec_rule`
- `feature_choice_option`
  - `id`, `choice_group_id`, `name`, `description`, `prereq_json`, `effects_json`
- `ancestry`
  - `id`, `ruleset_id`, `name`, `size_category`, `description`
- `ancestry_trait`
  - `id`, `ancestry_id`, `name`, `description`, `effects_json`
- `background`
  - `id`, `ruleset_id`, `name`, `description`
- `background_trait`
  - `id`, `background_id`, `name`, `description`, `prereq_json`, `effects_json`
- `skill`
  - `id`, `name`, `governing_stat`, `description`
- `language`
  - `id`, `name`, `description`
- `spell`
  - `id`, `ruleset_id`, `name`, `school`, `tier`, `is_cantrip`, `action_cost`, `mana_cost`, `description`
- `boon`
  - `id`, `ruleset_id`, `name`, `boon_tier` (`minor`, `major`, `epic`, `temporary`), `description`, `effects_json`
- `equipment_item`
  - `id`, `ruleset_id`, `name`, `category`, `slot_cost`, `armor_value_nullable`, `properties_json`

### B) Character state tables (mutable)

- `character`
  - `id`, `campaign_id_nullable`, `player_id_nullable`
  - `name`, `level`, `class_id`, `active_subclass_id_nullable`
  - `ancestry_id`, `background_id`, `motivation_text_nullable`
  - `height_text`, `weight_text`
  - `str_score`, `dex_score`, `int_score`, `wil_score`
  - `max_hp`, `current_hp`, `hit_die_type`, `max_hit_dice`, `current_hit_dice`
  - `max_wounds`, `current_wounds`
  - `initiative_bonus_cached`, `speed`, `inventory_slots_max`, `inventory_slots_used`
  - `gold`, `notes`
- `character_save_profile`
  - `character_id`, `str_save_state`, `dex_save_state`, `int_save_state`, `wil_save_state`
- `character_skill`
  - `character_id`, `skill_id`, `base_from_stat`, `allocated_points`, `misc_mod`, `total_value`
- `character_language`
  - `character_id`, `language_id`, `source_type` (`base`, `int_bonus`, `ancestry`, `feature`, etc.)
- `character_feature_selection`
  - `id`, `character_id`, `choice_group_id`, `option_id`, `selected_at_level`, `source` (`class`, `subclass`, `ancestry`, `background`, `boon`)
- `character_resource_pool`
  - `id`, `character_id`, `resource_code` (e.g. `mana`, `fury_dice`, `combat_dice`, `tot_hunt_charges`)
  - `max_value`, `current_value`, `die_size_nullable`, `refresh_rule`, `expires_rule`
- `character_spell_known`
  - `character_id`, `spell_id`, `source`, `is_prepared`, `notes`
- `character_inventory_item`
  - `id`, `character_id`, `item_id_nullable`, `custom_name_nullable`
  - `quantity`, `slot_cost_total`, `location` (`held`, `worn`, `packed`)
  - `is_equipped`, `metadata_json`
- `character_effect`
  - `id`, `character_id`, `effect_type` (`boon`, `condition`, `temporary_bonus`)
  - `source_ref`, `name`, `started_at`, `expires_on` (`end_of_encounter`, `next_safe_rest`, datetime)
  - `stacks`, `effects_json`
- `character_subclass_history`
  - `id`, `character_id`, `subclass_id`, `started_level`, `ended_level_nullable`, `change_reason`
- `character_level_log`
  - `id`, `character_id`, `new_level`, `gained_at`, `summary_json`
- `character_snapshot`
  - `id`, `character_id`, `created_at`, `snapshot_json`, `reason`

## Why This Model Fits Nimble

- Supports fixed catalogs (classes, ancestries, spells) plus campaign-time mutations.
- Handles class-specific mechanics without schema rewrites via `character_resource_pool`.
- Supports option-heavy progression through `feature_choice_group` + `character_feature_selection`.
- Preserves story changes (story-based subclasses, boon effects, temporary modifiers).
- Reconstructs full sheet state while still enabling efficient querying.

## Minimum V1 Persistence Contract

Before implementation, minimum required persisted data should include:

- identity and core stats
- class/subclass/ancestry/background
- level and progression choices
- all selected abilities/options
- HP/wounds/hit-dice/mana and other active resources
- skills, saves, languages
- equipment + slot usage
- active temporary effects and boons

## Generation and Customization Flows (V1)

### Flow A: Create New Character

1. Start new character and choose ruleset/version.
2. Choose class.
3. Choose ancestry and background.
4. Optionally set adventuring motivation text.
5. Assign base stats using allowed array presets.
6. Derive save profile, skill bases, secondary stats, and inventory slots.
7. Allocate level 1 skill points and any level 1 feature choices.
8. Assign starting gear or starting gold option, then validate slot usage.
9. Assign languages (Common plus INT-derived and feature-derived languages).
10. Run final validation and persist character + initial snapshot.

### Flow B: Create At Higher Starting Level

1. Complete Flow A with chosen start level.
2. For each level from 2 to target level, apply:
   - automatic class progression features
   - stat increases when granted
   - feature-choice selections when granted
   - subclass selection at level 3 (or GM-approved story-based subclass replacement if applicable)
3. Recalculate derived values and resource caps.
4. Persist completed sheet and level log entries.

### Flow C: Edit Existing Character (Non-Leveling)

1. Load current character sheet state.
2. Apply allowed edits (notes, inventory, effects, optional motivation updates, etc.).
3. Revalidate invariants (slot limits, legal references, resource bounds).
4. Persist updated state and optional snapshot.

### Flow D: Level Up Character

1. Increment level by one.
2. Apply automatic gains (HP increase, hit-die max, skill point gain, etc.).
3. Present any required choices for that level.
4. Validate all new choices and recalculated derived values.
5. Persist state and append level log.

### Flow E: Story-Based Subclass Replacement (GM Flow)

1. GM initiates subclass replacement action with reason/context.
2. Validate candidate subclass belongs to character class and is marked `is_story_based`.
3. End current subclass history record and start new one.
4. Apply subclass feature changes and required spell/feature deltas.
5. Persist swap and create audit snapshot.

### Flow F: Variant Character Copy (Snapshot-Based)

1. Select source snapshot.
2. Duplicate to a new character record in target campaign context.
3. Reset or retain fields based on copy mode (full clone vs template clone).
4. Persist as independent character lineage in V1 (no branching graph).

## Validation Rules and Constraints (V1)

### Core hard validations

- `character.class_id` is required and must exist.
- `character.active_subclass_id` must either be null or reference a subclass belonging to `class_id`.
- Exactly one active subclass at a time.
- Stats must use supported stat keys: `STR`, `DEX`, `INT`, `WIL`.
- Save profile must contain one advantaged save, one disadvantaged save, and two neutral saves (unless specific override effect is active).
- Skill totals must equal base + allocated + modifiers and remain within rule bounds.
- Inventory slot usage must not exceed `inventory_slots_max` unless explicit override flag is set.
- Resource pools cannot exceed max or drop below zero unless rule effect explicitly permits temporary overflow.
- Selected feature options must satisfy prerequisite constraints.
- Story-based subclass swaps must be initiated via GM-approved action path.

### Soft validations/warnings

- Missing adventuring motivation.
- Unspent skill points or unselected required options.
- Starting equipment mismatch with class/background defaults when not using gold-buy option.
- Orphaned temporary effects with expired `expires_on` timestamps.

## Test Requirements and Acceptance Conditions (V1)

### Required automated tests

1. Data integrity tests:
   - class/subclass FK compatibility
   - one active subclass invariant
   - feature choice prerequisite checks
2. Rules calculation tests:
   - inventory slot calculations (`10 + STR`)
   - language count derivation from INT and features
   - save profile and derived stat recalculation
3. Progression tests:
   - level-up grants and required choices
   - subclass selection at level 3
   - story-based subclass swap history correctness
4. Persistence tests:
   - create/load character round-trip
   - snapshot copy creates independent record
   - level log and subclass history append behavior

### Acceptance conditions for requirements readiness

1. A complete written flow exists for create, edit, level-up, story subclass swap, and snapshot clone.
2. Hard validation rules are documented and map cleanly to schema + service layer checks.
3. Required static catalogs (class/subclass/ancestry/skill/language/spell/boon) are identified.
4. V1 decisions and deferred scope are explicitly captured.
5. User confirms the documented behavior is acceptable for first implementation.

## V1 Decision Record (Open Questions Resolved)

### 1) Persistence strategy

Decision:

- Use direct mutable sheet updates as the source of truth.
- Keep `character_level_log` for major progression events (especially level-up).
- Keep `character_snapshot` for rollback/debug and timeline inspection.

Why:

- Much simpler to ship than full event sourcing.
- Still gives useful history/audit without requiring recompute pipelines.

### 2) Spell loadout modeling

Decision:

- V1 tracks spells as "known/unlocked", not "prepared".
- Keep `character_spell_known.is_prepared` as optional/unused for forward compatibility.

Why:

- Nimble progression and class text primarily model learned schools/spells and unlocked tiers.
- Avoids imposing a prepared-spell paradigm where it may not be needed.

### 3) Story-based subclass swaps and constraint strictness

Decision:

- Enforce hard DB compatibility rules:
  - `active_subclass_id` must belong to the character's class.
  - one active subclass at a time.
- Enforce story-based swap rules in application/service layer (GM-authorized flow), not rigid DB-level story checks.
- Always record swaps in `character_subclass_history` with reason metadata.

Why:

- Prevents invalid data while preserving narrative flexibility.
- Story triggers are campaign-contextual and better validated in domain logic than SQL constraints.

### 4) Ancestry/background mutability

Decision:

- Lock ancestry/background in standard player edit flow after character creation.
- Allow GM/admin override via explicit "override origin" action, with reason captured in audit notes/history.

Why:

- Keeps player-facing character identity stable.
- Still supports story transformations or correction of mistakes.

### 5) Character variants/clones across campaigns/timelines

Decision:

- Do not model full branching/variant timelines in V1 schema.
- V1 uses one canonical character record per campaign context.
- If a variant is needed, duplicate from latest `character_snapshot` into a new character record (explicit copy operation).

Why:

- Avoids significant complexity in first implementation.
- Snapshot-based copy gives a practical path for "alternate timeline" play without blocking launch.

### 6) Adventuring motivation field treatment

Decision:

- Keep `motivation_text` as an explicit first-class field on `character`.
- Treat as optional in V1 validation (warning when blank, not hard error).

Why:

- Core Rules explicitly include motivation prompts in creation guidance.
- It provides narrative value and future story-engine integration hooks without adding schema complexity.

## Deferred After V1

- Full event sourcing + deterministic recompute of full sheet state.
- First-class branching timelines and parent/child character lineage graph.
- Hard validation policy engine for campaign-specific subclass story triggers.
