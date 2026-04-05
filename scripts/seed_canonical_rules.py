#!/usr/bin/env python3
"""Seed canonical Nimble rules data into SQLite.

T3 goals covered:
- runnable seed command/workflow
- clean rebuild support
- deterministic ordering
- basic logging + failure reporting
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STAT_KEYS = {"STR", "DEX", "INT", "WIL"}
SIZE_CATEGORIES = {"tiny", "small", "medium", "large", "varies", "other"}
FEATURE_TYPES = {
    "auto",
    "choice_grant",
    "resource_change",
    "stat_increase",
    "spell_grant",
    "passive",
    "other",
}
RESPEC_RULES = {"never", "level_up_only", "gm_override", "anytime"}
BOON_TIERS = {"minor", "major", "epic", "temporary"}


class SeedError(RuntimeError):
    """Raised when seed input or reference integrity is invalid."""


@dataclass
class TableStat:
    inserted: int = 0
    updated: int = 0


@dataclass
class SeedStats:
    by_table: dict[str, TableStat] = field(default_factory=dict)

    def record(self, table: str, action: str) -> None:
        stat = self.by_table.setdefault(table, TableStat())
        if action == "inserted":
            stat.inserted += 1
        elif action == "updated":
            stat.updated += 1


class CanonicalSeeder:
    def __init__(self, conn: sqlite3.Connection, seed_dir: Path, stats: SeedStats):
        self.conn = conn
        self.seed_dir = seed_dir
        self.stats = stats

    def run(self) -> None:
        ruleset = self._load_object("ruleset")
        ruleset_id = self._seed_ruleset(ruleset)

        self._seed_skills(self._load_array("skills"))
        self._seed_languages(self._load_array("languages"))
        self._seed_classes(ruleset_id, self._load_array("classes"))
        self._seed_ancestries(ruleset_id, self._load_array("ancestries"))
        self._seed_backgrounds(ruleset_id, self._load_array("backgrounds"))
        self._seed_subclasses(ruleset_id, self._load_array("subclasses"))
        self._seed_ancestry_traits(ruleset_id, self._load_array("ancestry_traits"))
        self._seed_background_traits(ruleset_id, self._load_array("background_traits"))
        self._seed_class_level_features(ruleset_id, self._load_array("class_level_features"))
        self._seed_feature_choice_groups(ruleset_id, self._load_array("feature_choice_groups"))
        self._seed_feature_choice_options(ruleset_id, self._load_array("feature_choice_options"))
        self._seed_spells(ruleset_id, self._load_array("spells"))
        self._seed_boons(ruleset_id, self._load_array("boons"))
        self._seed_equipment_items(ruleset_id, self._load_array("equipment_items"))

    def _load_json(self, stem: str) -> Any:
        path = self.seed_dir / f"{stem}.json"
        if not path.exists():
            raise SeedError(f"Missing seed file: {path}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_array(self, stem: str) -> list[dict[str, Any]]:
        payload = self._load_json(stem)
        if not isinstance(payload, list):
            raise SeedError(f"Expected array in {stem}.json")
        for index, row in enumerate(payload):
            if not isinstance(row, dict):
                raise SeedError(f"Expected object rows in {stem}.json at index {index}")
        return payload

    def _load_object(self, stem: str) -> dict[str, Any]:
        payload = self._load_json(stem)
        if not isinstance(payload, dict):
            raise SeedError(f"Expected object in {stem}.json")
        return payload

    def _normalize_stat(self, value: str, context: str) -> str:
        candidate = str(value).strip().upper()
        if candidate not in STAT_KEYS:
            raise SeedError(f"Invalid stat '{value}' in {context}")
        return candidate

    def _normalize_size_category(self, value: Any, context: str) -> str | None:
        if value is None:
            return None
        candidate = str(value).strip().lower()
        if candidate not in SIZE_CATEGORIES:
            raise SeedError(f"Invalid size category '{value}' in {context}")
        return candidate

    def _normalize_feature_type(self, value: Any, context: str) -> str:
        candidate = str(value or "other").strip().lower()
        if candidate not in FEATURE_TYPES:
            raise SeedError(f"Invalid feature_type '{value}' in {context}")
        return candidate

    def _normalize_respec_rule(self, value: Any, context: str) -> str:
        candidate = str(value or "never").strip().lower()
        if candidate not in RESPEC_RULES:
            raise SeedError(f"Invalid respec_rule '{value}' in {context}")
        return candidate

    def _normalize_boon_tier(self, value: Any, context: str) -> str:
        candidate = str(value).strip().lower()
        if candidate not in BOON_TIERS:
            raise SeedError(f"Invalid boon_tier '{value}' in {context}")
        return candidate

    @staticmethod
    def _as_json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _as_bool_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int) and value in (0, 1):
            return value
        if isinstance(value, str):
            candidate = value.strip().lower()
            if candidate in {"1", "true", "yes", "y"}:
                return 1
            if candidate in {"0", "false", "no", "n"}:
                return 0
        raise SeedError(f"Unable to parse boolean value: {value!r}")

    def _upsert_by_key(
        self,
        table: str,
        key_where: str,
        key_args: tuple[Any, ...],
        update_values: dict[str, Any],
        insert_values: dict[str, Any],
    ) -> int:
        row = self.conn.execute(
            f"SELECT id FROM {table} WHERE {key_where}",
            key_args,
        ).fetchone()

        if row:
            set_clause = ", ".join(f"{column} = ?" for column in update_values)
            self.conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE id = ?",
                (*update_values.values(), int(row["id"])),
            )
            self.stats.record(table, "updated")
            return int(row["id"])

        columns = ", ".join(insert_values.keys())
        placeholders = ", ".join("?" for _ in insert_values)
        cursor = self.conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(insert_values.values()),
        )
        self.stats.record(table, "inserted")
        return int(cursor.lastrowid)

    def _require_text(self, row: dict[str, Any], key: str, context: str) -> str:
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SeedError(f"Missing required text '{key}' in {context}")
        return value.strip()

    def _require_int(self, row: dict[str, Any], key: str, context: str) -> int:
        value = row.get(key)
        try:
            result = int(value)
        except (TypeError, ValueError) as exc:
            raise SeedError(f"Missing/invalid integer '{key}' in {context}") from exc
        return result

    def _lookup_class_id(self, ruleset_id: int, class_name: str, context: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM character_class WHERE ruleset_id = ? AND name = ?",
            (ruleset_id, class_name),
        ).fetchone()
        if not row:
            raise SeedError(f"Unknown class '{class_name}' referenced in {context}")
        return int(row["id"])

    def _lookup_subclass_id(self, ruleset_id: int, class_id: int, subclass_name: str, context: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM subclass WHERE ruleset_id = ? AND class_id = ? AND name = ?",
            (ruleset_id, class_id, subclass_name),
        ).fetchone()
        if not row:
            raise SeedError(
                f"Unknown subclass '{subclass_name}' for class_id={class_id} referenced in {context}",
            )
        return int(row["id"])

    def _lookup_ancestry_id(self, ruleset_id: int, ancestry_name: str, context: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM ancestry WHERE ruleset_id = ? AND name = ?",
            (ruleset_id, ancestry_name),
        ).fetchone()
        if not row:
            raise SeedError(f"Unknown ancestry '{ancestry_name}' referenced in {context}")
        return int(row["id"])

    def _lookup_background_id(self, ruleset_id: int, background_name: str, context: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM background WHERE ruleset_id = ? AND name = ?",
            (ruleset_id, background_name),
        ).fetchone()
        if not row:
            raise SeedError(f"Unknown background '{background_name}' referenced in {context}")
        return int(row["id"])

    def _lookup_feature_choice_group_id(
        self,
        ruleset_id: int,
        class_id: int,
        subclass_id: int | None,
        group_name: str,
        context: str,
    ) -> int:
        if subclass_id is None:
            row = self.conn.execute(
                """
                SELECT id
                FROM feature_choice_group
                WHERE ruleset_id = ? AND class_id = ? AND subclass_id IS NULL AND name = ?
                """,
                (ruleset_id, class_id, group_name),
            ).fetchone()
        else:
            row = self.conn.execute(
                """
                SELECT id
                FROM feature_choice_group
                WHERE ruleset_id = ? AND class_id = ? AND subclass_id = ? AND name = ?
                """,
                (ruleset_id, class_id, subclass_id, group_name),
            ).fetchone()
        if not row:
            raise SeedError(
                f"Unknown feature choice group '{group_name}' referenced in {context}",
            )
        return int(row["id"])

    def _seed_ruleset(self, row: dict[str, Any]) -> int:
        name = self._require_text(row, "name", "ruleset")
        version = self._require_text(row, "version", "ruleset")

        source_book = row.get("source_book")
        if isinstance(source_book, list):
            source_book = " + ".join(sorted({str(item).strip() for item in source_book if str(item).strip()}))

        source_page_ref = row.get("source_page_ref")

        return self._upsert_by_key(
            table="ruleset",
            key_where="name = ? AND version = ?",
            key_args=(name, version),
            update_values={
                "source_book": source_book,
                "source_page_ref": source_page_ref,
            },
            insert_values={
                "name": name,
                "version": version,
                "source_book": source_book,
                "source_page_ref": source_page_ref,
            },
        )

    def _seed_skills(self, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"skill:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            governing_stat = self._normalize_stat(self._require_text(row, "governing_stat", context), context)
            description = row.get("description")

            self._upsert_by_key(
                table="skill",
                key_where="name = ?",
                key_args=(name,),
                update_values={
                    "governing_stat": governing_stat,
                    "description": description,
                },
                insert_values={
                    "name": name,
                    "governing_stat": governing_stat,
                    "description": description,
                },
            )

    def _seed_languages(self, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"language:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            description = row.get("description")

            self._upsert_by_key(
                table="language",
                key_where="name = ?",
                key_args=(name,),
                update_values={"description": description},
                insert_values={"name": name, "description": description},
            )

    def _seed_classes(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"class:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            hit_die = self._require_int(row, "hit_die", context)
            starting_hp = self._require_int(row, "starting_hp", context)
            key_stat_1 = self._normalize_stat(self._require_text(row, "key_stat_1", context), context)
            key_stat_2 = self._normalize_stat(self._require_text(row, "key_stat_2", context), context)
            save_adv_stat = self._normalize_stat(self._require_text(row, "save_adv_stat", context), context)
            save_disadv_stat = self._normalize_stat(self._require_text(row, "save_disadv_stat", context), context)
            if key_stat_1 == key_stat_2:
                raise SeedError(f"key_stat_1 and key_stat_2 cannot match in {context}")
            if save_adv_stat == save_disadv_stat:
                raise SeedError(f"save_adv_stat and save_disadv_stat cannot match in {context}")

            self._upsert_by_key(
                table="character_class",
                key_where="ruleset_id = ? AND name = ?",
                key_args=(ruleset_id, name),
                update_values={
                    "description": row.get("description"),
                    "hit_die": hit_die,
                    "starting_hp": starting_hp,
                    "key_stat_1": key_stat_1,
                    "key_stat_2": key_stat_2,
                    "save_adv_stat": save_adv_stat,
                    "save_disadv_stat": save_disadv_stat,
                    "armor_proficiencies_json": self._as_json(row.get("armor_proficiencies")),
                    "weapon_proficiencies_json": self._as_json(row.get("weapon_proficiencies")),
                    "starting_gear_json": self._as_json(row.get("starting_gear")),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "name": name,
                    "description": row.get("description"),
                    "hit_die": hit_die,
                    "starting_hp": starting_hp,
                    "key_stat_1": key_stat_1,
                    "key_stat_2": key_stat_2,
                    "save_adv_stat": save_adv_stat,
                    "save_disadv_stat": save_disadv_stat,
                    "armor_proficiencies_json": self._as_json(row.get("armor_proficiencies")),
                    "weapon_proficiencies_json": self._as_json(row.get("weapon_proficiencies")),
                    "starting_gear_json": self._as_json(row.get("starting_gear")),
                },
            )

    def _seed_subclasses(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("class_name", "").casefold(),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"subclass:{row.get('name', '<unknown>')}"
            class_name = self._require_text(row, "class_name", context)
            class_id = self._lookup_class_id(ruleset_id, class_name, context)
            name = self._require_text(row, "name", context)
            is_story_based = self._as_bool_int(row.get("is_story_based", 0))

            self._upsert_by_key(
                table="subclass",
                key_where="class_id = ? AND name = ?",
                key_args=(class_id, name),
                update_values={
                    "ruleset_id": ruleset_id,
                    "is_story_based": is_story_based,
                    "description": row.get("description"),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "class_id": class_id,
                    "name": name,
                    "is_story_based": is_story_based,
                    "description": row.get("description"),
                },
            )

    def _seed_ancestries(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"ancestry:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            size_category = self._normalize_size_category(row.get("size_category"), context)

            self._upsert_by_key(
                table="ancestry",
                key_where="ruleset_id = ? AND name = ?",
                key_args=(ruleset_id, name),
                update_values={
                    "size_category": size_category,
                    "description": row.get("description"),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "name": name,
                    "size_category": size_category,
                    "description": row.get("description"),
                },
            )

    def _seed_ancestry_traits(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("ancestry_name", "").casefold(),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"ancestry_trait:{row.get('name', '<unknown>')}"
            ancestry_name = self._require_text(row, "ancestry_name", context)
            ancestry_id = self._lookup_ancestry_id(ruleset_id, ancestry_name, context)
            name = self._require_text(row, "name", context)

            self._upsert_by_key(
                table="ancestry_trait",
                key_where="ancestry_id = ? AND name = ?",
                key_args=(ancestry_id, name),
                update_values={
                    "description": row.get("description"),
                    "effects_json": self._as_json(row.get("effects")),
                },
                insert_values={
                    "ancestry_id": ancestry_id,
                    "name": name,
                    "description": row.get("description"),
                    "effects_json": self._as_json(row.get("effects")),
                },
            )

    def _seed_backgrounds(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"background:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)

            self._upsert_by_key(
                table="background",
                key_where="ruleset_id = ? AND name = ?",
                key_args=(ruleset_id, name),
                update_values={"description": row.get("description")},
                insert_values={
                    "ruleset_id": ruleset_id,
                    "name": name,
                    "description": row.get("description"),
                },
            )

    def _seed_background_traits(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("background_name", "").casefold(),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"background_trait:{row.get('name', '<unknown>')}"
            background_name = self._require_text(row, "background_name", context)
            background_id = self._lookup_background_id(ruleset_id, background_name, context)
            name = self._require_text(row, "name", context)

            self._upsert_by_key(
                table="background_trait",
                key_where="background_id = ? AND name = ?",
                key_args=(background_id, name),
                update_values={
                    "description": row.get("description"),
                    "prereq_json": self._as_json(row.get("prereq")),
                    "effects_json": self._as_json(row.get("effects")),
                },
                insert_values={
                    "background_id": background_id,
                    "name": name,
                    "description": row.get("description"),
                    "prereq_json": self._as_json(row.get("prereq")),
                    "effects_json": self._as_json(row.get("effects")),
                },
            )

    def _seed_class_level_features(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("class_name", "").casefold(),
            (item.get("subclass_name") or "").casefold(),
            int(item.get("level", 0) or 0),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"class_level_feature:{row.get('name', '<unknown>')}"
            class_name = self._require_text(row, "class_name", context)
            class_id = self._lookup_class_id(ruleset_id, class_name, context)

            subclass_name = row.get("subclass_name")
            subclass_id: int | None = None
            if subclass_name:
                subclass_id = self._lookup_subclass_id(ruleset_id, class_id, str(subclass_name).strip(), context)

            level = self._require_int(row, "level", context)
            if level < 1 or level > 20:
                raise SeedError(f"Level out of range (1..20) in {context}: {level}")

            name = self._require_text(row, "name", context)
            feature_type = self._normalize_feature_type(row.get("feature_type"), context)
            display_order = int(row.get("display_order", 0))

            if subclass_id is None:
                key_where = "ruleset_id = ? AND class_id = ? AND subclass_id IS NULL AND level = ? AND name = ?"
                key_args = (ruleset_id, class_id, level, name)
            else:
                key_where = "ruleset_id = ? AND class_id = ? AND subclass_id = ? AND level = ? AND name = ?"
                key_args = (ruleset_id, class_id, subclass_id, level, name)

            self._upsert_by_key(
                table="class_level_feature",
                key_where=key_where,
                key_args=key_args,
                update_values={
                    "description": row.get("description"),
                    "feature_type": feature_type,
                    "display_order": display_order,
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "class_id": class_id,
                    "subclass_id": subclass_id,
                    "level": level,
                    "name": name,
                    "description": row.get("description"),
                    "feature_type": feature_type,
                    "display_order": display_order,
                },
            )

    def _seed_feature_choice_groups(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("class_name", "").casefold(),
            (item.get("subclass_name") or "").casefold(),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"feature_choice_group:{row.get('name', '<unknown>')}"
            class_name = self._require_text(row, "class_name", context)
            class_id = self._lookup_class_id(ruleset_id, class_name, context)

            subclass_name = row.get("subclass_name")
            subclass_id: int | None = None
            if subclass_name:
                subclass_id = self._lookup_subclass_id(ruleset_id, class_id, str(subclass_name).strip(), context)

            name = self._require_text(row, "name", context)
            max_choices = self._require_int(row, "max_choices", context)
            if max_choices <= 0:
                raise SeedError(f"max_choices must be > 0 in {context}")
            respec_rule = self._normalize_respec_rule(row.get("respec_rule"), context)

            if subclass_id is None:
                key_where = "ruleset_id = ? AND class_id = ? AND subclass_id IS NULL AND name = ?"
                key_args = (ruleset_id, class_id, name)
            else:
                key_where = "ruleset_id = ? AND class_id = ? AND subclass_id = ? AND name = ?"
                key_args = (ruleset_id, class_id, subclass_id, name)

            self._upsert_by_key(
                table="feature_choice_group",
                key_where=key_where,
                key_args=key_args,
                update_values={
                    "max_choices": max_choices,
                    "respec_rule": respec_rule,
                    "description": row.get("description"),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "class_id": class_id,
                    "subclass_id": subclass_id,
                    "name": name,
                    "max_choices": max_choices,
                    "respec_rule": respec_rule,
                    "description": row.get("description"),
                },
            )

    def _seed_feature_choice_options(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("class_name", "").casefold(),
            (item.get("subclass_name") or "").casefold(),
            item.get("group_name", "").casefold(),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"feature_choice_option:{row.get('name', '<unknown>')}"
            class_name = self._require_text(row, "class_name", context)
            class_id = self._lookup_class_id(ruleset_id, class_name, context)

            subclass_name = row.get("subclass_name")
            subclass_id: int | None = None
            if subclass_name:
                subclass_id = self._lookup_subclass_id(ruleset_id, class_id, str(subclass_name).strip(), context)

            group_name = self._require_text(row, "group_name", context)
            choice_group_id = self._lookup_feature_choice_group_id(
                ruleset_id,
                class_id,
                subclass_id,
                group_name,
                context,
            )
            name = self._require_text(row, "name", context)
            display_order = int(row.get("display_order", 0))

            self._upsert_by_key(
                table="feature_choice_option",
                key_where="choice_group_id = ? AND name = ?",
                key_args=(choice_group_id, name),
                update_values={
                    "description": row.get("description"),
                    "prereq_json": self._as_json(row.get("prereq")),
                    "effects_json": self._as_json(row.get("effects")),
                    "display_order": display_order,
                },
                insert_values={
                    "choice_group_id": choice_group_id,
                    "name": name,
                    "description": row.get("description"),
                    "prereq_json": self._as_json(row.get("prereq")),
                    "effects_json": self._as_json(row.get("effects")),
                    "display_order": display_order,
                },
            )

    def _seed_spells(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"spell:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            tier = self._require_int(row, "tier", context)
            if tier < 0:
                raise SeedError(f"tier must be >= 0 in {context}")

            is_cantrip = self._as_bool_int(row.get("is_cantrip", 0))
            mana_cost_raw = row.get("mana_cost")
            mana_cost: int | None = None
            if mana_cost_raw is not None:
                try:
                    mana_cost = int(mana_cost_raw)
                except (TypeError, ValueError) as exc:
                    raise SeedError(f"Invalid mana_cost in {context}") from exc
                if mana_cost < 0:
                    raise SeedError(f"mana_cost must be >= 0 in {context}")

            self._upsert_by_key(
                table="spell",
                key_where="ruleset_id = ? AND name = ?",
                key_args=(ruleset_id, name),
                update_values={
                    "school": row.get("school"),
                    "tier": tier,
                    "is_cantrip": is_cantrip,
                    "action_cost": row.get("action_cost"),
                    "mana_cost": mana_cost,
                    "description": row.get("description"),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "name": name,
                    "school": row.get("school"),
                    "tier": tier,
                    "is_cantrip": is_cantrip,
                    "action_cost": row.get("action_cost"),
                    "mana_cost": mana_cost,
                    "description": row.get("description"),
                },
            )

    def _seed_boons(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        for row in sorted(rows, key=lambda item: item.get("name", "").casefold()):
            context = f"boon:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            boon_tier = self._normalize_boon_tier(self._require_text(row, "boon_tier", context), context)

            self._upsert_by_key(
                table="boon",
                key_where="ruleset_id = ? AND name = ?",
                key_args=(ruleset_id, name),
                update_values={
                    "boon_tier": boon_tier,
                    "description": row.get("description"),
                    "effects_json": self._as_json(row.get("effects")),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "name": name,
                    "boon_tier": boon_tier,
                    "description": row.get("description"),
                    "effects_json": self._as_json(row.get("effects")),
                },
            )

    def _seed_equipment_items(self, ruleset_id: int, rows: list[dict[str, Any]]) -> None:
        sort_key = lambda item: (
            item.get("category", "").casefold(),
            item.get("name", "").casefold(),
        )
        for row in sorted(rows, key=sort_key):
            context = f"equipment:{row.get('name', '<unknown>')}"
            name = self._require_text(row, "name", context)
            category = self._require_text(row, "category", context)

            slot_cost_raw = row.get("slot_cost")
            try:
                slot_cost = float(slot_cost_raw)
            except (TypeError, ValueError) as exc:
                raise SeedError(f"Missing/invalid slot_cost in {context}") from exc
            if slot_cost < 0:
                raise SeedError(f"slot_cost must be >= 0 in {context}")

            armor_value_raw = row.get("armor_value")
            armor_value: int | None = None
            if armor_value_raw is not None:
                try:
                    armor_value = int(armor_value_raw)
                except (TypeError, ValueError) as exc:
                    raise SeedError(f"Invalid armor_value in {context}") from exc
                if armor_value < 0:
                    raise SeedError(f"armor_value must be >= 0 in {context}")

            self._upsert_by_key(
                table="equipment_item",
                key_where="ruleset_id = ? AND name = ?",
                key_args=(ruleset_id, name),
                update_values={
                    "category": category,
                    "slot_cost": slot_cost,
                    "armor_value": armor_value,
                    "properties_json": self._as_json(row.get("properties")),
                },
                insert_values={
                    "ruleset_id": ruleset_id,
                    "name": name,
                    "category": category,
                    "slot_cost": slot_cost,
                    "armor_value": armor_value,
                    "properties_json": self._as_json(row.get("properties")),
                },
            )


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def apply_migrations(conn: sqlite3.Connection, migrations_dir: Path) -> None:
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        raise SeedError(f"No migration files found in {migrations_dir}")

    for migration_file in migration_files:
        logging.info("Applying migration %s", migration_file.name)
        script = migration_file.read_text(encoding="utf-8")
        conn.executescript(script)


def schema_has_user_tables(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT COUNT(*) AS table_count
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """,
    ).fetchone()
    return int(row["table_count"]) > 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed canonical Nimble rules data into SQLite")
    parser.add_argument(
        "--db",
        default="database/nimble.sqlite",
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--migrations-dir",
        default="database/migrations",
        help="Path to SQL migrations directory",
    )
    parser.add_argument(
        "--seed-dir",
        default="database/seed_data/v1",
        help="Path to versioned seed data directory",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete DB file before running migrations + seed",
    )
    parser.add_argument(
        "--force-migrations",
        action="store_true",
        help="Apply migrations even if DB already has user tables",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip migration execution and seed into existing schema",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    db_path = Path(args.db)
    migrations_dir = Path(args.migrations_dir)
    seed_dir = Path(args.seed_dir)

    if args.rebuild and db_path.exists():
        logging.info("Removing existing DB for rebuild: %s", db_path)
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    stats = SeedStats()

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")

            has_tables = schema_has_user_tables(conn)

            if not args.skip_migrations:
                if args.force_migrations or not has_tables:
                    apply_migrations(conn, migrations_dir)
                else:
                    logging.info(
                        "Skipping migrations because DB already has user tables (use --force-migrations to reapply).",
                    )
            else:
                logging.info("Skipping migrations by request (--skip-migrations)")

            with conn:
                seeder = CanonicalSeeder(conn=conn, seed_dir=seed_dir, stats=stats)
                seeder.run()

            logging.info("Seed completed successfully.")
            for table_name in sorted(stats.by_table):
                table_stat = stats.by_table[table_name]
                logging.info(
                    "table=%s inserted=%d updated=%d",
                    table_name,
                    table_stat.inserted,
                    table_stat.updated,
                )

    except (sqlite3.Error, OSError, ValueError, SeedError, json.JSONDecodeError) as exc:
        logging.error("Seed failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
