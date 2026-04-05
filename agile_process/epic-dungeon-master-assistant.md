# Epic: Dungeon Master Assistant

## Epic Description

Build a Dungeon Master Assistant tool that combines a deterministic combat engine with LLM-driven story and roleplay components. The system should also include a player-facing character generator.

## Current Epic Status

- Status: In progress
- Owner: Team
- Goal: Provide DM support through combat automation, story narration, and character creation

## Stories

### Story 1: Core Combat Engine
- Status: backlog
- Description: Implement deterministic combat mechanics for initiative, turn order, condition handling, and encounter state.
- Success Criteria:
  - Combat turns resolve in a deterministic order
  - Initiative, HP, conditions, and status are tracked and persisted
  - Combat snapshots can be stored and retrieved
- Test Requirements:
  - Unit tests for initiative order and state transitions
  - Simulation tests for encounter resolution
  - Persistence tests for saving/loading snapshots

### Story 2: Story and Roleplay Orchestration
- Status: backlog
- Description: Build the LLM integration layer to generate narrative beats, NPC dialogue, and session summaries from game state.
- Success Criteria:
  - Story prompts can ingest game state and produce cohesive narrative output
  - NPC responses are generated based on context and roleplay rules
  - Summaries capture scene highlights and continuity
- Test Requirements:
  - Prompt validation and output sanity checks
  - Manual review of generated narration quality
  - Edge case handling for missing or malformed state

### Story 3: Character Generator
- Status: in progress
- Description: Provide a character creation tool for players to generate and customize characters, including archetypes, stats, and narrative hooks.
- Success Criteria:
  - Players can generate valid character sheets
  - Character archetypes include attributes, skills, and narrative flavor
  - Generated characters can be edited and saved
- Test Requirements:
  - Validate generated character schema
  - Verify save/load behavior
  - Review character creation flow for completeness
- Notes:
  - Requirements and schema/flow/test definitions are complete in the Character Generator Requirements epic.
  - Story 2.5 canonical rules SQLite milestone is implemented and in user-review state (see `agile_process/story-2.5-runbook.md`).

## Notes

- A story must be refined and approved before development begins.
- If requirements change, update this epic file and any impacted story sections.
