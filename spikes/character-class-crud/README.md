# Character Class CRUD Spike

This spike provides full CRUD workflows for `character_class` records, subclasses (`subclass`), class ability progression (`class_level_feature`), and optional ability sets/options (`feature_choice_group` + `feature_choice_option`) with a human-readable admin UI.

## Goals

- CRUD for character classes against `database/nimble.sqlite`
- CRUD for subclasses (including story-based flags)
- CRUD for class abilities/progression by level
- CRUD for optional ability sets and selectable options
- No PK/FK text boxes in UX
- Ruleset linkage handled through a dropdown (`ruleset.name` + `ruleset.version`)
- Enum-constrained fields (`key stats`, `save stats`) handled through select lists
- Feature type and subclass scope are handled through select lists
- Respec behavior is handled through a select list
- Friendly delete errors when dependent data blocks deletion

## Run

From repository root:

```bash
scripts/start-class-management-app.sh
```

Or run the server directly:

```bash
python3 spikes/character-class-crud/server.py --db database/nimble.sqlite
```

Open:

- `http://127.0.0.1:8765`

## UX Notes

- `id` and `ruleset_id` are never directly editable.
- If no rulesets exist, the form prompts you to create one first.
- Multi-value fields (armor, weapons, starting gear) are edited as one-per-line text, then serialized to JSON.

## API Endpoints

- `GET /api/health`
- `GET /api/rulesets`
- `POST /api/rulesets`
- `GET /api/classes`
- `GET /api/classes/:id`
- `POST /api/classes`
- `PUT /api/classes/:id`
- `DELETE /api/classes/:id`
- `GET /api/classes/:id/progression`
- `POST /api/classes/:id/progression`
- `PUT /api/progression/:id`
- `DELETE /api/progression/:id`
- `GET /api/classes/:id/subclasses`
- `POST /api/classes/:id/subclasses`
- `PUT /api/subclasses/:id`
- `DELETE /api/subclasses/:id`
- `GET /api/classes/:id/choice-groups`
- `POST /api/classes/:id/choice-groups`
- `PUT /api/choice-groups/:id`
- `DELETE /api/choice-groups/:id`
- `GET /api/choice-groups/:id/options`
- `POST /api/choice-groups/:id/options`
- `PUT /api/choice-options/:id`
- `DELETE /api/choice-options/:id`

## Scope Boundaries

- This spike targets `character_class`, `subclass`, `class_level_feature`, `feature_choice_group`, and `feature_choice_option` CRUD.
