PRAGMA foreign_keys = ON;

BEGIN;

-- V1 canonical rules domains for Story 2.5:
-- classes, subclasses, ancestries, backgrounds, skills, languages,
-- class/feature catalogs, spells, boons, and equipment reference rows.

CREATE TABLE ruleset (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    source_book TEXT,
    source_page_ref TEXT,
    UNIQUE (name, version)
);

CREATE TABLE character_class (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    hit_die INTEGER NOT NULL CHECK (hit_die > 0),
    starting_hp INTEGER NOT NULL CHECK (starting_hp > 0),
    key_stat_1 TEXT NOT NULL CHECK (key_stat_1 IN ('STR', 'DEX', 'INT', 'WIL')),
    key_stat_2 TEXT NOT NULL CHECK (key_stat_2 IN ('STR', 'DEX', 'INT', 'WIL')),
    save_adv_stat TEXT NOT NULL CHECK (save_adv_stat IN ('STR', 'DEX', 'INT', 'WIL')),
    save_disadv_stat TEXT NOT NULL CHECK (save_disadv_stat IN ('STR', 'DEX', 'INT', 'WIL')),
    armor_proficiencies_json TEXT,
    weapon_proficiencies_json TEXT,
    starting_gear_json TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (ruleset_id, name),
    CHECK (key_stat_1 <> key_stat_2),
    CHECK (save_adv_stat <> save_disadv_stat)
);

CREATE UNIQUE INDEX uq_character_class_id_ruleset ON character_class (id, ruleset_id);

CREATE TABLE subclass (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_story_based INTEGER NOT NULL DEFAULT 0 CHECK (is_story_based IN (0, 1)),
    description TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (class_id, ruleset_id)
        REFERENCES character_class (id, ruleset_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (class_id, name)
);

CREATE UNIQUE INDEX uq_subclass_id_class_ruleset ON subclass (id, class_id, ruleset_id);
CREATE INDEX idx_subclass_by_class ON subclass (class_id);
CREATE INDEX idx_subclass_story_based ON subclass (is_story_based, class_id);

CREATE TABLE class_level_feature (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    subclass_id INTEGER,
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 20),
    name TEXT NOT NULL,
    description TEXT,
    combat_usage_notes TEXT,
    feature_type TEXT NOT NULL CHECK (
        feature_type IN (
            'auto',
            'choice_grant',
            'resource_change',
            'stat_increase',
            'spell_grant',
            'passive',
            'other'
        )
    ),
    display_order INTEGER NOT NULL DEFAULT 0 CHECK (display_order >= 0),
    FOREIGN KEY (class_id, ruleset_id)
        REFERENCES character_class (id, ruleset_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (subclass_id, class_id, ruleset_id)
        REFERENCES subclass (id, class_id, ruleset_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_class_level_feature_general
    ON class_level_feature (ruleset_id, class_id, level, name)
    WHERE subclass_id IS NULL;

CREATE UNIQUE INDEX uq_class_level_feature_subclass
    ON class_level_feature (ruleset_id, class_id, subclass_id, level, name)
    WHERE subclass_id IS NOT NULL;

CREATE INDEX idx_class_level_feature_lookup
    ON class_level_feature (class_id, subclass_id, level, display_order);

CREATE TABLE feature_choice_group (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    subclass_id INTEGER,
    name TEXT NOT NULL,
    max_choices INTEGER NOT NULL CHECK (max_choices > 0),
    respec_rule TEXT NOT NULL DEFAULT 'never' CHECK (
        respec_rule IN ('never', 'level_up_only', 'gm_override', 'anytime')
    ),
    description TEXT,
    FOREIGN KEY (class_id, ruleset_id)
        REFERENCES character_class (id, ruleset_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (subclass_id, class_id, ruleset_id)
        REFERENCES subclass (id, class_id, ruleset_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_feature_choice_group_general
    ON feature_choice_group (ruleset_id, class_id, name)
    WHERE subclass_id IS NULL;

CREATE UNIQUE INDEX uq_feature_choice_group_subclass
    ON feature_choice_group (ruleset_id, class_id, subclass_id, name)
    WHERE subclass_id IS NOT NULL;

CREATE INDEX idx_feature_choice_group_lookup
    ON feature_choice_group (class_id, subclass_id);

CREATE TABLE feature_choice_option (
    id INTEGER PRIMARY KEY,
    choice_group_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    combat_usage_notes TEXT,
    prereq_json TEXT,
    effects_json TEXT,
    display_order INTEGER NOT NULL DEFAULT 0 CHECK (display_order >= 0),
    FOREIGN KEY (choice_group_id)
        REFERENCES feature_choice_group (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (choice_group_id, name)
);

CREATE INDEX idx_feature_choice_option_group
    ON feature_choice_option (choice_group_id, display_order);

CREATE TABLE ancestry (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    size_category TEXT CHECK (size_category IN ('tiny', 'small', 'medium', 'large', 'varies', 'other')),
    description TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (ruleset_id, name)
);

CREATE TABLE ancestry_trait (
    id INTEGER PRIMARY KEY,
    ancestry_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    effects_json TEXT,
    FOREIGN KEY (ancestry_id)
        REFERENCES ancestry (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (ancestry_id, name)
);

CREATE TABLE background (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (ruleset_id, name)
);

CREATE TABLE background_trait (
    id INTEGER PRIMARY KEY,
    background_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    prereq_json TEXT,
    effects_json TEXT,
    FOREIGN KEY (background_id)
        REFERENCES background (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (background_id, name)
);

CREATE TABLE skill (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    governing_stat TEXT NOT NULL CHECK (governing_stat IN ('STR', 'DEX', 'INT', 'WIL')),
    description TEXT
);

CREATE TABLE language (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE spell (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    school TEXT,
    tier INTEGER NOT NULL CHECK (tier >= 0),
    is_cantrip INTEGER NOT NULL DEFAULT 0 CHECK (is_cantrip IN (0, 1)),
    action_cost TEXT,
    mana_cost INTEGER CHECK (mana_cost IS NULL OR mana_cost >= 0),
    description TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (ruleset_id, name)
);

CREATE INDEX idx_spell_lookup ON spell (ruleset_id, tier, name);

CREATE TABLE boon (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    boon_tier TEXT NOT NULL CHECK (boon_tier IN ('minor', 'major', 'epic', 'temporary')),
    description TEXT,
    effects_json TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (ruleset_id, name)
);

CREATE INDEX idx_boon_lookup ON boon (ruleset_id, boon_tier, name);

CREATE TABLE equipment_item (
    id INTEGER PRIMARY KEY,
    ruleset_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    slot_cost REAL NOT NULL CHECK (slot_cost >= 0),
    armor_value INTEGER CHECK (armor_value IS NULL OR armor_value >= 0),
    properties_json TEXT,
    FOREIGN KEY (ruleset_id) REFERENCES ruleset(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (ruleset_id, name)
);

CREATE INDEX idx_equipment_lookup ON equipment_item (ruleset_id, category, name);

COMMIT;
