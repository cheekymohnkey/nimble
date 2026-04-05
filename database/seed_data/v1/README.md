# Seed Data v1

This folder contains versioned canonical seed inputs for Story 2.5.

Status for T4 (2026-04-05):

- Implemented deterministic seed pipeline and file contract.
- Populated V1 canonical domains for:
  - `ruleset`
  - `character_class`
  - `subclass` (including `is_story_based=1` rows for Oathbreaker, Spellblade, Reaver, Beastmaster)
  - `ancestry`
  - `ancestry_trait`
  - `background`
  - `background_trait`
  - `skill`
  - `language`
  - `class_level_feature`
  - `feature_choice_group`
  - `feature_choice_option`
  - `spell`
  - `boon`
  - `equipment_item`

Deferred domains/fields (intentional for V1):

- Structured effect grammar for traits/features/spells (`effects_json` remains minimally structured).
- Class-to-spell learnability matrix (requires additional relation table beyond current schema freeze).
- Campaign-policy metadata for story-triggered subclass swaps (service-layer concern).

Expected file contract:

- `ruleset.json` (object)
- domain arrays:
  - `classes.json`
  - `subclasses.json`
  - `ancestries.json`
  - `ancestry_traits.json`
  - `backgrounds.json`
  - `background_traits.json`
  - `skills.json`
  - `languages.json`
  - `class_level_features.json`
  - `feature_choice_groups.json`
  - `feature_choice_options.json`
  - `spells.json`
  - `boons.json`
  - `equipment_items.json`
