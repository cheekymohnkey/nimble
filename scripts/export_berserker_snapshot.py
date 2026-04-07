#!/usr/bin/env python3
"""Export Berserker rows from SQLite into a normalized JSON snapshot."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.replace("’", "'").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_json(value: str | None) -> Any:
    if value is None or value == "":
        return None
    return json.loads(value)


def export_snapshot(db_path: Path) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        class_row = conn.execute(
            """
            SELECT
                c.id,
                c.ruleset_id,
                c.name,
                c.description,
                c.hit_die,
                c.starting_hp,
                c.key_stat_1,
                c.key_stat_2,
                c.save_adv_stat,
                c.save_disadv_stat,
                c.armor_proficiencies_json,
                c.weapon_proficiencies_json,
                c.starting_gear_json,
                r.name AS ruleset_name,
                r.version AS ruleset_version
            FROM character_class c
            JOIN ruleset r ON r.id = c.ruleset_id
            WHERE c.name = 'Berserker'
            """,
        ).fetchone()
        if class_row is None:
            raise RuntimeError("Berserker class not found in DB")

        class_id = int(class_row["id"])
        subclasses = conn.execute(
            """
            SELECT id, name, is_story_based, description
            FROM subclass
            WHERE class_id = ?
            ORDER BY name
            """,
            (class_id,),
        ).fetchall()
        subclass_lookup = {int(row["id"]): row["name"] for row in subclasses}

        progression = conn.execute(
            """
            SELECT level, subclass_id, name, feature_type, display_order, description
            FROM class_level_feature
            WHERE class_id = ?
            ORDER BY level, CASE WHEN subclass_id IS NULL THEN 0 ELSE 1 END, display_order, name
            """,
            (class_id,),
        ).fetchall()

        groups = conn.execute(
            """
            SELECT id, subclass_id, name, max_choices, respec_rule, description
            FROM feature_choice_group
            WHERE class_id = ?
            ORDER BY CASE WHEN subclass_id IS NULL THEN 0 ELSE 1 END, name
            """,
            (class_id,),
        ).fetchall()
        group_lookup = {
            int(row["id"]): {
                "name": row["name"],
                "scopeSubclass": (
                    subclass_lookup.get(int(row["subclass_id"]))
                    if row["subclass_id"] is not None
                    else None
                ),
            }
            for row in groups
        }

        options = conn.execute(
            """
            SELECT choice_group_id, name, description, prereq_json, effects_json, display_order
            FROM feature_choice_option
            WHERE choice_group_id IN (SELECT id FROM feature_choice_group WHERE class_id = ?)
            ORDER BY choice_group_id, display_order, name
            """,
            (class_id,),
        ).fetchall()

    snapshot = {
        "ruleset": {
            "name": class_row["ruleset_name"],
            "version": class_row["ruleset_version"],
        },
        "class": {
            "name": class_row["name"],
            "description": normalize_text(class_row["description"]),
            "hitDie": int(class_row["hit_die"]),
            "startingHp": int(class_row["starting_hp"]),
            "keyStat1": class_row["key_stat_1"],
            "keyStat2": class_row["key_stat_2"],
            "saveAdvStat": class_row["save_adv_stat"],
            "saveDisadvStat": class_row["save_disadv_stat"],
            "armorProficiencies": parse_json(class_row["armor_proficiencies_json"]),
            "weaponProficiencies": parse_json(class_row["weapon_proficiencies_json"]),
            "startingGear": parse_json(class_row["starting_gear_json"]),
        },
        "subclasses": [
            {
                "name": row["name"],
                "isStoryBased": bool(row["is_story_based"]),
                "description": normalize_text(row["description"]),
            }
            for row in subclasses
        ],
        "progression": [
            {
                "level": int(row["level"]),
                "scopeSubclass": (
                    subclass_lookup.get(int(row["subclass_id"]))
                    if row["subclass_id"] is not None
                    else None
                ),
                "name": row["name"],
                "featureType": row["feature_type"],
                "displayOrder": int(row["display_order"]),
                "description": normalize_text(row["description"]),
            }
            for row in progression
        ],
        "choiceGroups": [
            {
                "scopeSubclass": (
                    subclass_lookup.get(int(row["subclass_id"]))
                    if row["subclass_id"] is not None
                    else None
                ),
                "name": row["name"],
                "maxChoices": int(row["max_choices"]),
                "respecRule": row["respec_rule"],
                "description": normalize_text(row["description"]),
            }
            for row in groups
        ],
        "choiceOptions": [
            {
                "scopeSubclass": group_lookup[int(row["choice_group_id"])]["scopeSubclass"],
                "groupName": group_lookup[int(row["choice_group_id"])]["name"],
                "name": row["name"],
                "displayOrder": int(row["display_order"]),
                "description": normalize_text(row["description"]),
                "prereq": parse_json(row["prereq_json"]),
                "effects": parse_json(row["effects_json"]),
            }
            for row in options
        ],
    }
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Berserker snapshot from SQLite")
    parser.add_argument("--db", required=True, help="SQLite DB path")
    parser.add_argument("--out", help="Output JSON file path (stdout if omitted)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = export_snapshot(Path(args.db))
    text = json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
