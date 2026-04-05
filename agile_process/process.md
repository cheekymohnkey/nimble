# Agile Work Process

This folder contains epic tracking and handover documentation for the `nimble` project.

## Workflow Rules

1. Before writing any code, require a well-documented story with:
   - clear description
   - success criteria
   - test requirements
   - acceptance conditions

2. Refine stories by asking questions when requirements are unclear or incomplete.

3. Only write code once the story is sufficiently detailed and the user has approved the scope.

4. When a feature is complete enough for user testing, inform the user and ask them to test the feature.

5. When requirements change:
   - update the requirements documentation
   - mark affected stories as updated or incomplete
   - reflect the changes in the epic file
   - update `handover.md` with the next best story to complete
   - remove any unnecessary detail about previously completed stories from `handover.md`

## Epic and Story File Format

- Each epic is tracked in its own markdown file in this folder.
- Each story should include:
  - `Story:` title and description
  - `Status:` backlog / in progress / ready for review / done
  - `Success Criteria:` measurable outcomes
  - `Test Requirements:` what to verify
  - `Notes:` clarifications or open questions

## Handover Responsibilities

- `handover.md` always reflects the current next best story to work on.
- Completed stories are not carried forward as active work in `handover.md`.
- Unnecessary detail about finished work should be removed from `handover.md`.
- If a story is partially complete, it may stay in `handover.md` until the next best actionable task is defined.

## Communication Expectations

- Make the process explicit in documentation before each implementation phase.
- Ask the user for confirmation when major scope decisions or story refinements are required.
- Keep the user informed when a feature is ready for user testing.
