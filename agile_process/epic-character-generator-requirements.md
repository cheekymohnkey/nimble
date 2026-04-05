# Epic: Character Generator Requirements Gathering

## Epic Description

Collect and define requirements for the Dungeon Master Assistant character generator. The epic should capture all key user needs, design decisions, and validation criteria before implementation begins.

## Goal

Create a complete, user-approved requirements set for the player-facing character generator, including:
- generation flows
- character archetypes
- stats and traits
- customization options
- persistence and editing
- integration points with the story engine and campaign data

## Current Epic Status

- Status: In progress
- Owner: Team
- Objective: Requirements are approved; Story 2.5 implementation is complete and pending user review

## Stories

### Story 1: Requirement Interviews and Clarifications
- Status: done
- Description: Ask the user key questions about how the character generator should work, what character data must be included, and how players will interact with it.
- Success Criteria:
  - The user has answered all requirement questions
  - The team has a confirmed list of character generator features
  - Ambiguities are identified and resolved
- Test Requirements:
  - Review the Q&A and ensure no open questions remain
  - Validate that the story covers both player-facing and DM-facing needs
- Acceptance Conditions:
  - All open design questions have explicit V1 decisions or are marked as deferred scope
  - User confirms the decision record is acceptable for implementation planning
- Notes:
  - Decision outcomes are documented in `documentation/character-generation-requirements.md` under "V1 Decision Record (Open Questions Resolved)".

### Story 1.5: Extract Official Book Character Definitions
- Status: done
- Description: Gather character creation rules, ancestry options, class/subclass details, and feature structures from the official Nimble PDFs.
- Success Criteria:
  - All relevant character-related content is extracted from the official books
  - Class and subclass lists are documented
  - Ancestry and background structure is documented
  - The character data model reflects the source material accurately
- Test Requirements:
  - Confirm the extracted definitions against the book source
  - Ensure the proposed data model supports all captured fields and choices
- Acceptance Conditions:
  - Class, subclass, ancestry, and key character-sheet requirements are documented in one requirements source
  - Story-based subclass handling is explicitly documented in both requirements and data model notes
- Notes:
  - Extracted outcomes are captured in `documentation/character-generation-requirements.md`.

### Story 2: Define Character Data Model
- Status: done
- Description: Specify the schema for generated characters, including fields for archetype, abilities, skills, background, and narrative hooks.
- Success Criteria:
  - A complete character schema is documented
  - Required and optional fields are identified
  - Integration points with campaign and story systems are noted
- Test Requirements:
  - Confirm schema completeness with the user
  - Ensure the model supports both generation and editing
- Acceptance Conditions:
  - Static definitions and mutable state are separated in the schema design
  - Required entities and relationships are listed for class, subclass, features, resources, inventory, and effects
  - V1 constraints vs deferred concerns are clearly called out
- Notes:
  - Initial schema proposal is documented in `documentation/character-generation-requirements.md`.

### Story 2.5: Persist Canonical Rules Data to SQLite
- Status: ready for review
- Description: Materialize official character reference data into SQLite tables so runtime character generation/editing uses database-backed canonical rules data.
- Success Criteria:
  - SQLite tables exist for canonical character rules domains (class, subclass, ancestry, background, skills, languages, abilities/features, spells, and related catalogs required by the final schema).
  - Official-source character data is extracted and seeded into those tables.
  - Seeded data is internally consistent (valid foreign keys and class/subclass compatibility).
  - The seed process is repeatable and can rebuild the canonical rules catalog from source files.
- Test Requirements:
  - Verify representative row coverage per domain (classes, subclasses, ancestries, backgrounds, spells, abilities/features).
  - Validate referential integrity and required uniqueness constraints.
  - Run seed process on a clean SQLite database and confirm deterministic results.
- Acceptance Conditions:
  - Character generator backend can resolve all V1 character creation choices from SQLite lookup tables instead of hardcoded constants.
  - Story-based subclasses are represented in the same subclass domain with explicit flagging/metadata.
  - Any deferred domains are explicitly listed and excluded by design (not by omission).
- Notes:
  - This story is implementation-phase and should begin only after requirements sign-off.
  - Requirements sign-off has been completed; implementation tasks T1-T6 are complete.
  - Execution checklist: `agile_process/story-2.5-execution-checklist.md`.
  - Runbook and traceability: `agile_process/story-2.5-runbook.md`.
  - Implementation Checklist:
    1. Finalize SQLite schema/migration for canonical rules tables.
    2. Define source-to-table mapping for classes, subclasses, ancestries, backgrounds, skills, languages, features/abilities, and spells.
    3. Build repeatable seed pipeline (idempotent or clean-rebuild path).
    4. Seed initial canonical dataset from official extracted definitions.
    5. Add integrity checks (FK validity, uniqueness, class/subclass compatibility).
    6. Add coverage checks for representative row counts per domain.
    7. Document deferred domains explicitly and mark them out of V1 scope.

### Story 3: Define Generation and Customization Flow
- Status: done
- Description: Document the user flows for generating, customizing, saving, and editing characters.
- Success Criteria:
  - Flow diagrams or written steps cover all major actions
  - Success criteria for each flow step are defined
  - Edge cases are considered (e.g. incomplete input, revisions, invalid combinations)
- Test Requirements:
  - Validate flows with the user before implementation
  - Ensure the process is clear for frontend and backend work
- Acceptance Conditions:
  - Written V1 flows exist for create, higher-level create, edit, level-up, story-based subclass replacement, and snapshot copy
  - Flow steps map cleanly to persistence actions and validation checkpoints
- Notes:
  - Flow definitions are documented in `documentation/character-generation-requirements.md`.

### Story 4: Define Validation and Testing Requirements
- Status: done
- Description: Establish the acceptance tests and validation rules for generated characters.
- Success Criteria:
  - Test cases for character schema validation are listed
  - Rules for valid character generation are documented
  - User acceptance criteria are aligned with the requirements
- Test Requirements:
  - Confirm the test plan with the user
  - Ensure the acceptance criteria are actionable and measurable
- Acceptance Conditions:
  - Hard validation rules and warning-level validations are documented
  - Automated test categories are specified for integrity, calculation, progression, and persistence
  - Requirements readiness acceptance checklist is documented and user-reviewable
- Notes:
  - Validation and test sections are documented in `documentation/character-generation-requirements.md`.

## Notes

- No code should be written until these requirements are documented and approved.
- If any requirement changes, update this epic and the corresponding stories immediately.
- The handover file should reflect this epic while it is the next best item to complete.
