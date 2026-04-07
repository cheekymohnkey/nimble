#!/usr/bin/env python3
"""Character class CRUD spike server.

A lightweight JSON API + static UI server using only Python stdlib.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STAT_OPTIONS = ("STR", "DEX", "INT", "WIL")
FEATURE_TYPE_OPTIONS = (
    "auto",
    "choice_grant",
    "resource_change",
    "stat_increase",
    "spell_grant",
    "passive",
    "other",
)
RESPEC_RULE_OPTIONS = ("never", "level_up_only", "gm_override", "anytime")


@dataclass
class AppConfig:
    db_path: Path
    migration_path: Path
    static_dir: Path


def ensure_schema(db_path: Path, migration_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        row = conn.execute(
            """
            SELECT count(*) AS table_count
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchone()
        assert row is not None
        if int(row["table_count"]) == 0:
            sql = migration_path.read_text(encoding="utf-8")
            conn.executescript(sql)

        ensure_optional_columns(conn)


def ensure_optional_columns(conn: sqlite3.Connection) -> None:
    table_columns: dict[str, set[str]] = {}
    for table_name in ("class_level_feature", "feature_choice_option"):
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        table_columns[table_name] = {str(row["name"]) for row in rows}

    if "combat_usage_notes" not in table_columns["class_level_feature"]:
        conn.execute("ALTER TABLE class_level_feature ADD COLUMN combat_usage_notes TEXT")

    if "combat_usage_notes" not in table_columns["feature_choice_option"]:
        conn.execute("ALTER TABLE feature_choice_option ADD COLUMN combat_usage_notes TEXT")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_optional_columns(conn)
    return conn


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_stat(name: str, value: Any) -> str:
    text = clean_text(value).upper()
    if text not in STAT_OPTIONS:
        raise ValueError(f"{name} must be one of {', '.join(STAT_OPTIONS)}")
    return text


def normalize_positive_int(name: str, value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a whole number") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return parsed


def normalize_non_negative_int(name: str, value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a whole number") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be 0 or greater")
    return parsed


def normalize_level(name: str, value: Any) -> int:
    level = normalize_positive_int(name, value)
    if level < 1 or level > 20:
        raise ValueError(f"{name} must be between 1 and 20")
    return level


def normalize_optional_positive_int(name: str, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and clean_text(value) == "":
        return None
    return normalize_positive_int(name, value)


def normalize_optional_json_text(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Allow freeform entry while still storing valid JSON.
        return json.dumps({"text": text}, ensure_ascii=False)

    return json.dumps(parsed, ensure_ascii=False)


def normalize_bool(name: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ValueError(f"{name} must be true or false")


def normalize_string_list(name: str, raw: Any) -> list[str]:
    if raw is None:
        return []

    if isinstance(raw, str):
        candidates = [piece for line in raw.splitlines() for piece in line.split(",")]
        values = [clean_text(piece) for piece in candidates if clean_text(piece)]
        return values

    if isinstance(raw, list):
        values: list[str] = []
        for entry in raw:
            item = clean_text(entry)
            if item:
                values.append(item)
        return values

    raise ValueError(f"{name} must be a list of text values")


def normalize_starting_gear(raw: Any) -> list[str] | dict[str, Any]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        return raw
    return normalize_string_list("startingGear", raw)


def parse_json_text(raw: str | None) -> Any:
    if raw is None or raw == "":
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Keep malformed legacy payloads readable in UI.
        return [raw]


def parse_optional_json_text(raw: str | None) -> Any | None:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Keep malformed legacy payloads readable in UI.
        return raw


def hydrate_class_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "hitDie": int(row["hit_die"]),
        "startingHp": int(row["starting_hp"]),
        "keyStat1": row["key_stat_1"],
        "keyStat2": row["key_stat_2"],
        "saveAdvStat": row["save_adv_stat"],
        "saveDisadvStat": row["save_disadv_stat"],
        "armorProficiencies": parse_json_text(row["armor_proficiencies_json"]),
        "weaponProficiencies": parse_json_text(row["weapon_proficiencies_json"]),
        "startingGear": parse_json_text(row["starting_gear_json"]),
        "ruleset": {
            "id": int(row["ruleset_id"]),
            "name": row["ruleset_name"],
            "version": row["ruleset_version"],
            "sourceBook": row["ruleset_source_book"],
            "sourcePageRef": row["ruleset_source_page_ref"],
        },
    }


def parse_class_payload(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}

    def has(key: str) -> bool:
        return key in payload and payload[key] is not None

    if not partial or has("rulesetId"):
        data["ruleset_id"] = normalize_positive_int("rulesetId", payload.get("rulesetId"))

    if not partial or has("name"):
        name = clean_text(payload.get("name"))
        if not name:
            raise ValueError("name is required")
        data["name"] = name

    if not partial or has("description"):
        description = clean_text(payload.get("description"))
        data["description"] = description if description else None

    if not partial or has("hitDie"):
        data["hit_die"] = normalize_positive_int("hitDie", payload.get("hitDie"))

    if not partial or has("startingHp"):
        data["starting_hp"] = normalize_positive_int("startingHp", payload.get("startingHp"))

    if not partial or has("keyStat1"):
        data["key_stat_1"] = normalize_stat("keyStat1", payload.get("keyStat1"))

    if not partial or has("keyStat2"):
        data["key_stat_2"] = normalize_stat("keyStat2", payload.get("keyStat2"))

    if not partial or has("saveAdvStat"):
        data["save_adv_stat"] = normalize_stat("saveAdvStat", payload.get("saveAdvStat"))

    if not partial or has("saveDisadvStat"):
        data["save_disadv_stat"] = normalize_stat("saveDisadvStat", payload.get("saveDisadvStat"))

    if not partial or has("armorProficiencies"):
        armor = normalize_string_list("armorProficiencies", payload.get("armorProficiencies"))
        data["armor_proficiencies_json"] = json.dumps(armor, ensure_ascii=False)

    if not partial or has("weaponProficiencies"):
        weapons = normalize_string_list("weaponProficiencies", payload.get("weaponProficiencies"))
        data["weapon_proficiencies_json"] = json.dumps(weapons, ensure_ascii=False)

    if not partial or has("startingGear"):
        gear = normalize_starting_gear(payload.get("startingGear"))
        data["starting_gear_json"] = json.dumps(gear, ensure_ascii=False)

    key_1 = data.get("key_stat_1")
    key_2 = data.get("key_stat_2")
    if key_1 and key_2 and key_1 == key_2:
        raise ValueError("Primary and secondary key stats must be different")

    adv = data.get("save_adv_stat")
    disadv = data.get("save_disadv_stat")
    if adv and disadv and adv == disadv:
        raise ValueError("Save advantage and disadvantage stats must be different")

    return data


def parse_ruleset_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = clean_text(payload.get("name"))
    version = clean_text(payload.get("version"))
    source_book = clean_text(payload.get("sourceBook"))
    source_page_ref = clean_text(payload.get("sourcePageRef"))

    if not name:
        raise ValueError("ruleset name is required")
    if not version:
        raise ValueError("ruleset version is required")

    return {
        "name": name,
        "version": version,
        "source_book": source_book if source_book else None,
        "source_page_ref": source_page_ref if source_page_ref else None,
    }


def parse_progression_payload(payload: dict[str, Any]) -> dict[str, Any]:
    level = normalize_level("level", payload.get("level"))
    name = clean_text(payload.get("name"))
    if not name:
        raise ValueError("ability name is required")

    feature_type = clean_text(payload.get("featureType"))
    if feature_type not in FEATURE_TYPE_OPTIONS:
        raise ValueError(f"featureType must be one of {', '.join(FEATURE_TYPE_OPTIONS)}")

    description = clean_text(payload.get("description"))
    combat_usage_notes = clean_text(payload.get("combatUsageNotes"))
    display_order = normalize_non_negative_int("displayOrder", payload.get("displayOrder", 0))
    subclass_id = normalize_optional_positive_int("subclassId", payload.get("subclassId"))

    return {
        "level": level,
        "name": name,
        "description": description if description else None,
        "combat_usage_notes": combat_usage_notes if combat_usage_notes else None,
        "feature_type": feature_type,
        "display_order": display_order,
        "subclass_id": subclass_id,
    }


def parse_subclass_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = clean_text(payload.get("name"))
    if not name:
        raise ValueError("subclass name is required")

    is_story_based = normalize_bool("isStoryBased", payload.get("isStoryBased", False))
    description = clean_text(payload.get("description"))

    return {
        "name": name,
        "is_story_based": int(is_story_based),
        "description": description if description else None,
    }


def parse_choice_group_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = clean_text(payload.get("name"))
    if not name:
        raise ValueError("group name is required")

    max_choices = normalize_positive_int("maxChoices", payload.get("maxChoices"))

    respec_rule = clean_text(payload.get("respecRule"))
    if respec_rule not in RESPEC_RULE_OPTIONS:
        raise ValueError(f"respecRule must be one of {', '.join(RESPEC_RULE_OPTIONS)}")

    description = clean_text(payload.get("description"))
    subclass_id = normalize_optional_positive_int("subclassId", payload.get("subclassId"))

    return {
        "name": name,
        "max_choices": max_choices,
        "respec_rule": respec_rule,
        "description": description if description else None,
        "subclass_id": subclass_id,
    }


def parse_choice_option_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = clean_text(payload.get("name"))
    if not name:
        raise ValueError("option name is required")

    description = clean_text(payload.get("description"))
    combat_usage_notes = clean_text(payload.get("combatUsageNotes"))
    display_order = normalize_non_negative_int("displayOrder", payload.get("displayOrder", 0))
    prereq_json = normalize_optional_json_text(payload.get("prereqJson"))
    effects_json = normalize_optional_json_text(payload.get("effectsJson"))

    return {
        "name": name,
        "description": description if description else None,
        "combat_usage_notes": combat_usage_notes if combat_usage_notes else None,
        "display_order": display_order,
        "prereq_json": prereq_json,
        "effects_json": effects_json,
    }


def hydrate_progression_row(row: sqlite3.Row) -> dict[str, Any]:
    subclass_id = row["subclass_id"]
    subclass: dict[str, Any] | None = None
    if subclass_id is not None:
        subclass = {
            "id": int(subclass_id),
            "name": row["subclass_name"],
            "isStoryBased": bool(row["subclass_story_based"]),
        }

    return {
        "id": int(row["id"]),
        "level": int(row["level"]),
        "name": row["name"],
        "description": row["description"],
        "combatUsageNotes": row["combat_usage_notes"],
        "featureType": row["feature_type"],
        "displayOrder": int(row["display_order"]),
        "subclass": subclass,
    }


def hydrate_subclass_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "classId": int(row["class_id"]),
        "rulesetId": int(row["ruleset_id"]),
        "name": row["name"],
        "isStoryBased": bool(row["is_story_based"]),
        "description": row["description"],
    }


def hydrate_choice_group_row(row: sqlite3.Row) -> dict[str, Any]:
    subclass_id = row["subclass_id"]
    subclass: dict[str, Any] | None = None
    if subclass_id is not None:
        subclass = {
            "id": int(subclass_id),
            "name": row["subclass_name"],
            "isStoryBased": bool(row["subclass_story_based"]),
        }

    option_count = row["option_count"]
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "maxChoices": int(row["max_choices"]),
        "respecRule": row["respec_rule"],
        "description": row["description"],
        "subclass": subclass,
        "optionCount": int(option_count) if option_count is not None else 0,
    }


def hydrate_choice_option_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "combatUsageNotes": row["combat_usage_notes"],
        "displayOrder": int(row["display_order"]),
        "prereq": parse_optional_json_text(row["prereq_json"]),
        "effects": parse_optional_json_text(row["effects_json"]),
    }


class SpikeHandler(BaseHTTPRequestHandler):
    server_version = "CharacterClassSpike/0.1"

    @property
    def app_config(self) -> AppConfig:
        return self.server.app_config  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            json_response(self, HTTPStatus.OK, {"ok": True})
            return

        if path == "/api/rulesets":
            self.list_rulesets()
            return

        if path == "/api/classes":
            self.list_classes()
            return

        if path.startswith("/api/classes/") and path.endswith("/progression"):
            class_id = self.parse_class_subresource_id(path, "progression")
            if class_id is None:
                return
            self.list_class_progression(class_id)
            return

        if path.startswith("/api/classes/") and path.endswith("/subclasses"):
            class_id = self.parse_class_subresource_id(path, "subclasses")
            if class_id is None:
                return
            self.list_class_subclasses(class_id)
            return

        if path.startswith("/api/classes/") and path.endswith("/choice-groups"):
            class_id = self.parse_class_subresource_id(path, "choice-groups")
            if class_id is None:
                return
            self.list_class_choice_groups(class_id)
            return

        if path.startswith("/api/choice-groups/") and path.endswith("/options"):
            group_id = self.parse_choice_group_subresource_id(path, "options")
            if group_id is None:
                return
            self.list_choice_group_options(group_id)
            return

        if path.startswith("/api/classes/"):
            class_id = self.parse_class_id(path)
            if class_id is None:
                return
            self.get_class(class_id)
            return

        self.serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/api/rulesets":
            self.create_ruleset()
            return

        if path == "/api/classes":
            self.create_class()
            return

        if path.startswith("/api/classes/") and path.endswith("/progression"):
            class_id = self.parse_class_subresource_id(path, "progression")
            if class_id is None:
                return
            self.create_progression_feature(class_id)
            return

        if path.startswith("/api/classes/") and path.endswith("/subclasses"):
            class_id = self.parse_class_subresource_id(path, "subclasses")
            if class_id is None:
                return
            self.create_subclass(class_id)
            return

        if path.startswith("/api/classes/") and path.endswith("/choice-groups"):
            class_id = self.parse_class_subresource_id(path, "choice-groups")
            if class_id is None:
                return
            self.create_choice_group(class_id)
            return

        if path.startswith("/api/choice-groups/") and path.endswith("/options"):
            group_id = self.parse_choice_group_subresource_id(path, "options")
            if group_id is None:
                return
            self.create_choice_option(group_id)
            return

        json_response(self, HTTPStatus.NOT_FOUND, {"error": "Route not found"})

    def do_PUT(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/progression/"):
            feature_id = self.parse_feature_id(path)
            if feature_id is None:
                return
            self.update_progression_feature(feature_id)
            return

        if path.startswith("/api/subclasses/"):
            subclass_id = self.parse_subclass_id(path)
            if subclass_id is None:
                return
            self.update_subclass(subclass_id)
            return

        if path.startswith("/api/choice-groups/"):
            group_id = self.parse_choice_group_id(path)
            if group_id is None:
                return
            self.update_choice_group(group_id)
            return

        if path.startswith("/api/choice-options/"):
            option_id = self.parse_choice_option_id(path)
            if option_id is None:
                return
            self.update_choice_option(option_id)
            return

        if path.startswith("/api/classes/"):
            class_id = self.parse_class_id(path)
            if class_id is None:
                return
            self.update_class(class_id)
            return

        json_response(self, HTTPStatus.NOT_FOUND, {"error": "Route not found"})

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/progression/"):
            feature_id = self.parse_feature_id(path)
            if feature_id is None:
                return
            self.delete_progression_feature(feature_id)
            return

        if path.startswith("/api/subclasses/"):
            subclass_id = self.parse_subclass_id(path)
            if subclass_id is None:
                return
            self.delete_subclass(subclass_id)
            return

        if path.startswith("/api/choice-groups/"):
            group_id = self.parse_choice_group_id(path)
            if group_id is None:
                return
            self.delete_choice_group(group_id)
            return

        if path.startswith("/api/choice-options/"):
            option_id = self.parse_choice_option_id(path)
            if option_id is None:
                return
            self.delete_choice_option(option_id)
            return

        if path.startswith("/api/classes/"):
            class_id = self.parse_class_id(path)
            if class_id is None:
                return
            self.delete_class(class_id)
            return

        json_response(self, HTTPStatus.NOT_FOUND, {"error": "Route not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep logs concise and easy to scan during the spike.
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} - {fmt % args}")

    def parse_body_json(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length header")

        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON") from exc

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")

        return payload

    def parse_positive_id(self, raw_value: str, label: str) -> int | None:
        try:
            parsed = int(raw_value)
        except ValueError:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"{label} must be an integer"})
            return None

        if parsed <= 0:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"{label} must be positive"})
            return None

        return parsed

    def parse_class_id(self, path: str) -> int | None:
        prefix = "/api/classes/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid class route"})
            return None

        suffix = path[len(prefix) :]
        if "/" in suffix:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid class route"})
            return None

        return self.parse_positive_id(suffix, "Class ID")

    def parse_class_subresource_id(self, path: str, resource: str) -> int | None:
        prefix = "/api/classes/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid class route"})
            return None

        suffix = path[len(prefix) :]
        class_token, sep, tail = suffix.partition("/")
        if sep == "" or tail != resource:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid class subresource route"})
            return None

        return self.parse_positive_id(class_token, "Class ID")

    def parse_feature_id(self, path: str) -> int | None:
        prefix = "/api/progression/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid progression route"})
            return None

        suffix = path[len(prefix) :]
        if "/" in suffix:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid progression route"})
            return None

        return self.parse_positive_id(suffix, "Feature ID")

    def parse_subclass_id(self, path: str) -> int | None:
        prefix = "/api/subclasses/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid subclass route"})
            return None

        suffix = path[len(prefix) :]
        if "/" in suffix:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid subclass route"})
            return None

        return self.parse_positive_id(suffix, "Subclass ID")

    def parse_choice_group_id(self, path: str) -> int | None:
        prefix = "/api/choice-groups/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid choice group route"})
            return None

        suffix = path[len(prefix) :]
        if "/" in suffix:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid choice group route"})
            return None

        return self.parse_positive_id(suffix, "Choice Group ID")

    def parse_choice_group_subresource_id(self, path: str, resource: str) -> int | None:
        prefix = "/api/choice-groups/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid choice group route"})
            return None

        suffix = path[len(prefix) :]
        group_token, sep, tail = suffix.partition("/")
        if sep == "" or tail != resource:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid choice group subresource route"})
            return None

        return self.parse_positive_id(group_token, "Choice Group ID")

    def parse_choice_option_id(self, path: str) -> int | None:
        prefix = "/api/choice-options/"
        if not path.startswith(prefix):
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid choice option route"})
            return None

        suffix = path[len(prefix) :]
        if "/" in suffix:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Invalid choice option route"})
            return None

        return self.parse_positive_id(suffix, "Choice Option ID")

    def class_identity_row(self, conn: sqlite3.Connection, class_id: int) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT id, ruleset_id, name FROM character_class WHERE id = ?",
            (class_id,),
        ).fetchone()

    def validate_subclass_scope(
        self,
        conn: sqlite3.Connection,
        *,
        class_id: int,
        ruleset_id: int,
        subclass_id: int | None,
    ) -> None:
        if subclass_id is None:
            return

        row = conn.execute(
            """
            SELECT id
            FROM subclass
            WHERE id = ? AND class_id = ? AND ruleset_id = ?
            """,
            (subclass_id, class_id, ruleset_id),
        ).fetchone()
        if row is None:
            raise ValueError("Selected subclass is not valid for this class.")

    def progression_row_by_id(self, conn: sqlite3.Connection, feature_id: int) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT
                f.id,
                f.class_id,
                f.ruleset_id,
                f.subclass_id,
                f.level,
                f.name,
                f.description,
                f.combat_usage_notes,
                f.feature_type,
                f.display_order,
                s.name AS subclass_name,
                s.is_story_based AS subclass_story_based
            FROM class_level_feature AS f
            LEFT JOIN subclass AS s ON s.id = f.subclass_id
            WHERE f.id = ?
            """,
            (feature_id,),
        ).fetchone()

    def subclass_row_by_id(self, conn: sqlite3.Connection, subclass_id: int) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT id, ruleset_id, class_id, name, is_story_based, description
            FROM subclass
            WHERE id = ?
            """,
            (subclass_id,),
        ).fetchone()

    def choice_group_row_by_id(self, conn: sqlite3.Connection, group_id: int) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT
                g.id,
                g.ruleset_id,
                g.class_id,
                g.subclass_id,
                g.name,
                g.max_choices,
                g.respec_rule,
                g.description,
                s.name AS subclass_name,
                s.is_story_based AS subclass_story_based,
                (
                  SELECT COUNT(*)
                  FROM feature_choice_option AS o
                  WHERE o.choice_group_id = g.id
                ) AS option_count
            FROM feature_choice_group AS g
            LEFT JOIN subclass AS s ON s.id = g.subclass_id
            WHERE g.id = ?
            """,
            (group_id,),
        ).fetchone()

    def choice_option_row_by_id(self, conn: sqlite3.Connection, option_id: int) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT
                o.id,
                o.choice_group_id,
                o.name,
                o.description,
                o.combat_usage_notes,
                o.prereq_json,
                o.effects_json,
                o.display_order
            FROM feature_choice_option AS o
            WHERE o.id = ?
            """,
            (option_id,),
        ).fetchone()

    def serve_static(self, path: str) -> None:
        static_root = self.app_config.static_dir.resolve()
        relative = "index.html" if path in {"/", ""} else path.lstrip("/")
        file_path = (static_root / relative).resolve()

        if not str(file_path).startswith(str(static_root)):
            json_response(self, HTTPStatus.FORBIDDEN, {"error": "Forbidden path"})
            return

        if not file_path.exists() or not file_path.is_file():
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "File not found"})
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        content_type = mime_type or "application/octet-stream"
        body = file_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def list_rulesets(self) -> None:
        with connect(self.app_config.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, name, version, source_book, source_page_ref
                FROM ruleset
                ORDER BY name, version
                """
            ).fetchall()

        rulesets = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "version": row["version"],
                "sourceBook": row["source_book"],
                "sourcePageRef": row["source_page_ref"],
            }
            for row in rows
        ]
        json_response(self, HTTPStatus.OK, {"rulesets": rulesets})

    def create_ruleset(self) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_ruleset_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO ruleset (name, version, source_book, source_page_ref)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        parsed["name"],
                        parsed["version"],
                        parsed["source_book"],
                        parsed["source_page_ref"],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                json_response(
                    self,
                    HTTPStatus.CONFLICT,
                    {"error": "That ruleset name + version already exists."},
                )
                return

            row = conn.execute(
                "SELECT id, name, version, source_book, source_page_ref FROM ruleset WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()

        assert row is not None
        json_response(
            self,
            HTTPStatus.CREATED,
            {
                "ruleset": {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "version": row["version"],
                    "sourceBook": row["source_book"],
                    "sourcePageRef": row["source_page_ref"],
                }
            },
        )

    def list_classes(self) -> None:
        with connect(self.app_config.db_path) as conn:
            rows = conn.execute(
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
                    r.version AS ruleset_version,
                    r.source_book AS ruleset_source_book,
                    r.source_page_ref AS ruleset_source_page_ref
                FROM character_class AS c
                JOIN ruleset AS r ON r.id = c.ruleset_id
                ORDER BY r.name, r.version, c.name
                """
            ).fetchall()

        classes = [hydrate_class_row(row) for row in rows]
        json_response(self, HTTPStatus.OK, {"classes": classes})

    def get_class(self, class_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            row = conn.execute(
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
                    r.version AS ruleset_version,
                    r.source_book AS ruleset_source_book,
                    r.source_page_ref AS ruleset_source_page_ref
                FROM character_class AS c
                JOIN ruleset AS r ON r.id = c.ruleset_id
                WHERE c.id = ?
                """,
                (class_id,),
            ).fetchone()

        if row is None:
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
            return

        json_response(self, HTTPStatus.OK, {"class": hydrate_class_row(row)})

    def create_class(self) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_class_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            ruleset_row = conn.execute("SELECT id FROM ruleset WHERE id = ?", (parsed["ruleset_id"],)).fetchone()
            if ruleset_row is None:
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Selected ruleset does not exist"})
                return

            try:
                cur = conn.execute(
                    """
                    INSERT INTO character_class (
                        ruleset_id,
                        name,
                        description,
                        hit_die,
                        starting_hp,
                        key_stat_1,
                        key_stat_2,
                        save_adv_stat,
                        save_disadv_stat,
                        armor_proficiencies_json,
                        weapon_proficiencies_json,
                        starting_gear_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        parsed["ruleset_id"],
                        parsed["name"],
                        parsed["description"],
                        parsed["hit_die"],
                        parsed["starting_hp"],
                        parsed["key_stat_1"],
                        parsed["key_stat_2"],
                        parsed["save_adv_stat"],
                        parsed["save_disadv_stat"],
                        parsed["armor_proficiencies_json"],
                        parsed["weapon_proficiencies_json"],
                        parsed["starting_gear_json"],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed: character_class.ruleset_id, character_class.name" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "A class with this name already exists in the selected ruleset."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = conn.execute(
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
                    r.version AS ruleset_version,
                    r.source_book AS ruleset_source_book,
                    r.source_page_ref AS ruleset_source_page_ref
                FROM character_class AS c
                JOIN ruleset AS r ON r.id = c.ruleset_id
                WHERE c.id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()

        assert row is not None
        json_response(self, HTTPStatus.CREATED, {"class": hydrate_class_row(row)})

    def update_class(self, class_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_class_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            existing = conn.execute("SELECT id FROM character_class WHERE id = ?", (class_id,)).fetchone()
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            ruleset_row = conn.execute("SELECT id FROM ruleset WHERE id = ?", (parsed["ruleset_id"],)).fetchone()
            if ruleset_row is None:
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Selected ruleset does not exist"})
                return

            try:
                conn.execute(
                    """
                    UPDATE character_class
                    SET
                        ruleset_id = ?,
                        name = ?,
                        description = ?,
                        hit_die = ?,
                        starting_hp = ?,
                        key_stat_1 = ?,
                        key_stat_2 = ?,
                        save_adv_stat = ?,
                        save_disadv_stat = ?,
                        armor_proficiencies_json = ?,
                        weapon_proficiencies_json = ?,
                        starting_gear_json = ?
                    WHERE id = ?
                    """,
                    (
                        parsed["ruleset_id"],
                        parsed["name"],
                        parsed["description"],
                        parsed["hit_die"],
                        parsed["starting_hp"],
                        parsed["key_stat_1"],
                        parsed["key_stat_2"],
                        parsed["save_adv_stat"],
                        parsed["save_disadv_stat"],
                        parsed["armor_proficiencies_json"],
                        parsed["weapon_proficiencies_json"],
                        parsed["starting_gear_json"],
                        class_id,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed: character_class.ruleset_id, character_class.name" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "A class with this name already exists in the selected ruleset."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = conn.execute(
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
                    r.version AS ruleset_version,
                    r.source_book AS ruleset_source_book,
                    r.source_page_ref AS ruleset_source_page_ref
                FROM character_class AS c
                JOIN ruleset AS r ON r.id = c.ruleset_id
                WHERE c.id = ?
                """,
                (class_id,),
            ).fetchone()

        assert row is not None
        json_response(self, HTTPStatus.OK, {"class": hydrate_class_row(row)})

    def delete_class(self, class_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            existing = conn.execute(
                "SELECT id, name FROM character_class WHERE id = ?",
                (class_id,),
            ).fetchone()
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            dependents = conn.execute(
                """
                SELECT
                    (SELECT count(*) FROM subclass WHERE class_id = ?) AS subclasses,
                    (SELECT count(*) FROM class_level_feature WHERE class_id = ?) AS features,
                    (SELECT count(*) FROM feature_choice_group WHERE class_id = ?) AS choice_groups
                """,
                (class_id, class_id, class_id),
            ).fetchone()
            assert dependents is not None

            blockers = {
                "subclasses": int(dependents["subclasses"]),
                "classLevelFeatures": int(dependents["features"]),
                "featureChoiceGroups": int(dependents["choice_groups"]),
            }

            if any(blockers.values()):
                json_response(
                    self,
                    HTTPStatus.CONFLICT,
                    {
                        "error": "Cannot delete this class while linked records still exist.",
                        "blockers": blockers,
                    },
                )
                return

            conn.execute("DELETE FROM character_class WHERE id = ?", (class_id,))
            conn.commit()

        json_response(self, HTTPStatus.OK, {"deleted": True, "id": class_id})

    def list_class_subclasses(self, class_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            class_row = self.class_identity_row(conn, class_id)
            if class_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            subclass_rows = conn.execute(
                """
                SELECT id, ruleset_id, class_id, name, is_story_based, description
                FROM subclass
                WHERE class_id = ?
                ORDER BY name
                """,
                (class_id,),
            ).fetchall()

        subclasses = [hydrate_subclass_row(row) for row in subclass_rows]
        json_response(
            self,
            HTTPStatus.OK,
            {
                "classId": class_id,
                "className": class_row["name"],
                "subclasses": subclasses,
            },
        )

    def create_subclass(self, class_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_subclass_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            class_row = self.class_identity_row(conn, class_id)
            if class_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            ruleset_id = int(class_row["ruleset_id"])
            try:
                cur = conn.execute(
                    """
                    INSERT INTO subclass (
                        ruleset_id,
                        class_id,
                        name,
                        is_story_based,
                        description
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        ruleset_id,
                        class_id,
                        parsed["name"],
                        parsed["is_story_based"],
                        parsed["description"],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed: subclass.class_id, subclass.name" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "A subclass with this name already exists for this class."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.subclass_row_by_id(conn, int(cur.lastrowid))

        assert row is not None
        json_response(
            self,
            HTTPStatus.CREATED,
            {"classId": class_id, "subclass": hydrate_subclass_row(row)},
        )

    def update_subclass(self, subclass_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_subclass_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            existing = self.subclass_row_by_id(conn, subclass_id)
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Subclass not found"})
                return

            class_id = int(existing["class_id"])
            try:
                conn.execute(
                    """
                    UPDATE subclass
                    SET
                        name = ?,
                        is_story_based = ?,
                        description = ?
                    WHERE id = ?
                    """,
                    (
                        parsed["name"],
                        parsed["is_story_based"],
                        parsed["description"],
                        subclass_id,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed: subclass.class_id, subclass.name" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "A subclass with this name already exists for this class."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.subclass_row_by_id(conn, subclass_id)

        assert row is not None
        json_response(
            self,
            HTTPStatus.OK,
            {"classId": class_id, "subclass": hydrate_subclass_row(row)},
        )

    def delete_subclass(self, subclass_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            existing = self.subclass_row_by_id(conn, subclass_id)
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Subclass not found"})
                return

            class_id = int(existing["class_id"])
            blockers_row = conn.execute(
                """
                SELECT
                    (SELECT count(*) FROM class_level_feature WHERE subclass_id = ?) AS features,
                    (SELECT count(*) FROM feature_choice_group WHERE subclass_id = ?) AS choice_groups
                """,
                (subclass_id, subclass_id),
            ).fetchone()
            assert blockers_row is not None

            blockers = {
                "classLevelFeatures": int(blockers_row["features"]),
                "featureChoiceGroups": int(blockers_row["choice_groups"]),
            }
            if any(blockers.values()):
                json_response(
                    self,
                    HTTPStatus.CONFLICT,
                    {
                        "error": "Cannot delete this subclass while linked records still exist.",
                        "blockers": blockers,
                    },
                )
                return

            conn.execute("DELETE FROM subclass WHERE id = ?", (subclass_id,))
            conn.commit()

        json_response(
            self,
            HTTPStatus.OK,
            {"deleted": True, "id": subclass_id, "classId": class_id},
        )

    def list_class_progression(self, class_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            class_row = self.class_identity_row(conn, class_id)
            if class_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            subclass_rows = conn.execute(
                """
                SELECT id, name, is_story_based
                FROM subclass
                WHERE class_id = ?
                ORDER BY name
                """,
                (class_id,),
            ).fetchall()

            feature_rows = conn.execute(
                """
                SELECT
                    f.id,
                    f.class_id,
                    f.ruleset_id,
                    f.subclass_id,
                    f.level,
                    f.name,
                    f.description,
                    f.combat_usage_notes,
                    f.feature_type,
                    f.display_order,
                    s.name AS subclass_name,
                    s.is_story_based AS subclass_story_based
                FROM class_level_feature AS f
                LEFT JOIN subclass AS s ON s.id = f.subclass_id
                WHERE f.class_id = ?
                ORDER BY
                    f.level,
                    CASE WHEN f.subclass_id IS NULL THEN 0 ELSE 1 END,
                    f.display_order,
                    f.name
                """,
                (class_id,),
            ).fetchall()

        subclasses = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "isStoryBased": bool(row["is_story_based"]),
            }
            for row in subclass_rows
        ]
        features = [hydrate_progression_row(row) for row in feature_rows]
        json_response(
            self,
            HTTPStatus.OK,
            {
                "classId": class_id,
                "className": class_row["name"],
                "subclasses": subclasses,
                "features": features,
                "featureTypeOptions": list(FEATURE_TYPE_OPTIONS),
            },
        )

    def create_progression_feature(self, class_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_progression_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            class_row = self.class_identity_row(conn, class_id)
            if class_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            ruleset_id = int(class_row["ruleset_id"])
            try:
                self.validate_subclass_scope(
                    conn,
                    class_id=class_id,
                    ruleset_id=ruleset_id,
                    subclass_id=parsed["subclass_id"],
                )
            except ValueError as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            try:
                cur = conn.execute(
                    """
                    INSERT INTO class_level_feature (
                        ruleset_id,
                        class_id,
                        subclass_id,
                        level,
                        name,
                        description,
                        combat_usage_notes,
                        feature_type,
                        display_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ruleset_id,
                        class_id,
                        parsed["subclass_id"],
                        parsed["level"],
                        parsed["name"],
                        parsed["description"],
                        parsed["combat_usage_notes"],
                        parsed["feature_type"],
                        parsed["display_order"],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed" in msg or "uq_class_level_feature_" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "An ability with that name already exists for that level/scope."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.progression_row_by_id(conn, int(cur.lastrowid))

        assert row is not None
        json_response(
            self,
            HTTPStatus.CREATED,
            {"classId": class_id, "feature": hydrate_progression_row(row)},
        )

    def update_progression_feature(self, feature_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_progression_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            existing = self.progression_row_by_id(conn, feature_id)
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Ability progression row not found"})
                return

            class_id = int(existing["class_id"])
            ruleset_id = int(existing["ruleset_id"])
            try:
                self.validate_subclass_scope(
                    conn,
                    class_id=class_id,
                    ruleset_id=ruleset_id,
                    subclass_id=parsed["subclass_id"],
                )
            except ValueError as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            try:
                conn.execute(
                    """
                    UPDATE class_level_feature
                    SET
                        subclass_id = ?,
                        level = ?,
                        name = ?,
                        description = ?,
                        combat_usage_notes = ?,
                        feature_type = ?,
                        display_order = ?
                    WHERE id = ?
                    """,
                    (
                        parsed["subclass_id"],
                        parsed["level"],
                        parsed["name"],
                        parsed["description"],
                        parsed["combat_usage_notes"],
                        parsed["feature_type"],
                        parsed["display_order"],
                        feature_id,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed" in msg or "uq_class_level_feature_" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "An ability with that name already exists for that level/scope."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.progression_row_by_id(conn, feature_id)

        assert row is not None
        json_response(
            self,
            HTTPStatus.OK,
            {"classId": class_id, "feature": hydrate_progression_row(row)},
        )

    def delete_progression_feature(self, feature_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            row = conn.execute(
                "SELECT id, class_id FROM class_level_feature WHERE id = ?",
                (feature_id,),
            ).fetchone()
            if row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Ability progression row not found"})
                return

            class_id = int(row["class_id"])
            conn.execute("DELETE FROM class_level_feature WHERE id = ?", (feature_id,))
            conn.commit()

        json_response(
            self,
            HTTPStatus.OK,
            {"deleted": True, "id": feature_id, "classId": class_id},
        )

    def list_class_choice_groups(self, class_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            class_row = self.class_identity_row(conn, class_id)
            if class_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            subclass_rows = conn.execute(
                """
                SELECT id, name, is_story_based
                FROM subclass
                WHERE class_id = ?
                ORDER BY name
                """,
                (class_id,),
            ).fetchall()

            group_rows = conn.execute(
                """
                SELECT
                    g.id,
                    g.ruleset_id,
                    g.class_id,
                    g.subclass_id,
                    g.name,
                    g.max_choices,
                    g.respec_rule,
                    g.description,
                    s.name AS subclass_name,
                    s.is_story_based AS subclass_story_based,
                    (
                      SELECT COUNT(*)
                      FROM feature_choice_option AS o
                      WHERE o.choice_group_id = g.id
                    ) AS option_count
                FROM feature_choice_group AS g
                LEFT JOIN subclass AS s ON s.id = g.subclass_id
                WHERE g.class_id = ?
                ORDER BY
                    CASE WHEN g.subclass_id IS NULL THEN 0 ELSE 1 END,
                    g.name
                """,
                (class_id,),
            ).fetchall()

        subclasses = [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "isStoryBased": bool(row["is_story_based"]),
            }
            for row in subclass_rows
        ]
        groups = [hydrate_choice_group_row(row) for row in group_rows]
        json_response(
            self,
            HTTPStatus.OK,
            {
                "classId": class_id,
                "className": class_row["name"],
                "subclasses": subclasses,
                "groups": groups,
                "respecRuleOptions": list(RESPEC_RULE_OPTIONS),
            },
        )

    def create_choice_group(self, class_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_choice_group_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            class_row = self.class_identity_row(conn, class_id)
            if class_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Character class not found"})
                return

            ruleset_id = int(class_row["ruleset_id"])
            try:
                self.validate_subclass_scope(
                    conn,
                    class_id=class_id,
                    ruleset_id=ruleset_id,
                    subclass_id=parsed["subclass_id"],
                )
            except ValueError as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            try:
                cur = conn.execute(
                    """
                    INSERT INTO feature_choice_group (
                        ruleset_id,
                        class_id,
                        subclass_id,
                        name,
                        max_choices,
                        respec_rule,
                        description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ruleset_id,
                        class_id,
                        parsed["subclass_id"],
                        parsed["name"],
                        parsed["max_choices"],
                        parsed["respec_rule"],
                        parsed["description"],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed" in msg or "uq_feature_choice_group_" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "A choice group with that name already exists in this scope."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.choice_group_row_by_id(conn, int(cur.lastrowid))

        assert row is not None
        json_response(
            self,
            HTTPStatus.CREATED,
            {"classId": class_id, "group": hydrate_choice_group_row(row)},
        )

    def update_choice_group(self, group_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_choice_group_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            existing = self.choice_group_row_by_id(conn, group_id)
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Choice group not found"})
                return

            class_id = int(existing["class_id"])
            ruleset_id = int(existing["ruleset_id"])
            try:
                self.validate_subclass_scope(
                    conn,
                    class_id=class_id,
                    ruleset_id=ruleset_id,
                    subclass_id=parsed["subclass_id"],
                )
            except ValueError as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            try:
                conn.execute(
                    """
                    UPDATE feature_choice_group
                    SET
                        subclass_id = ?,
                        name = ?,
                        max_choices = ?,
                        respec_rule = ?,
                        description = ?
                    WHERE id = ?
                    """,
                    (
                        parsed["subclass_id"],
                        parsed["name"],
                        parsed["max_choices"],
                        parsed["respec_rule"],
                        parsed["description"],
                        group_id,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed" in msg or "uq_feature_choice_group_" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "A choice group with that name already exists in this scope."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.choice_group_row_by_id(conn, group_id)

        assert row is not None
        json_response(
            self,
            HTTPStatus.OK,
            {"classId": class_id, "group": hydrate_choice_group_row(row)},
        )

    def delete_choice_group(self, group_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            row = conn.execute(
                "SELECT id, class_id FROM feature_choice_group WHERE id = ?",
                (group_id,),
            ).fetchone()
            if row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Choice group not found"})
                return

            class_id = int(row["class_id"])
            conn.execute("DELETE FROM feature_choice_group WHERE id = ?", (group_id,))
            conn.commit()

        json_response(
            self,
            HTTPStatus.OK,
            {"deleted": True, "id": group_id, "classId": class_id},
        )

    def list_choice_group_options(self, group_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            group_row = self.choice_group_row_by_id(conn, group_id)
            if group_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Choice group not found"})
                return

            option_rows = conn.execute(
                """
                SELECT
                    o.id,
                    o.choice_group_id,
                    o.name,
                    o.description,
                    o.combat_usage_notes,
                    o.prereq_json,
                    o.effects_json,
                    o.display_order
                FROM feature_choice_option AS o
                WHERE o.choice_group_id = ?
                ORDER BY o.display_order, o.name
                """,
                (group_id,),
            ).fetchall()

        options = [hydrate_choice_option_row(row) for row in option_rows]
        json_response(
            self,
            HTTPStatus.OK,
            {
                "groupId": group_id,
                "classId": int(group_row["class_id"]),
                "group": hydrate_choice_group_row(group_row),
                "options": options,
            },
        )

    def create_choice_option(self, group_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_choice_option_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            group_row = self.choice_group_row_by_id(conn, group_id)
            if group_row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Choice group not found"})
                return

            try:
                cur = conn.execute(
                    """
                    INSERT INTO feature_choice_option (
                        choice_group_id,
                        name,
                        description,
                        combat_usage_notes,
                        prereq_json,
                        effects_json,
                        display_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        group_id,
                        parsed["name"],
                        parsed["description"],
                        parsed["combat_usage_notes"],
                        parsed["prereq_json"],
                        parsed["effects_json"],
                        parsed["display_order"],
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed: feature_choice_option.choice_group_id, feature_choice_option.name" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "An option with that name already exists in this group."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.choice_option_row_by_id(conn, int(cur.lastrowid))

        assert row is not None
        json_response(
            self,
            HTTPStatus.CREATED,
            {
                "groupId": group_id,
                "classId": int(group_row["class_id"]),
                "option": hydrate_choice_option_row(row),
            },
        )

    def update_choice_option(self, option_id: int) -> None:
        try:
            payload = self.parse_body_json()
            parsed = parse_choice_option_payload(payload)
        except ValueError as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        with connect(self.app_config.db_path) as conn:
            existing = self.choice_option_row_by_id(conn, option_id)
            if existing is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Choice option not found"})
                return

            group_id = int(existing["choice_group_id"])
            group_row = self.choice_group_row_by_id(conn, group_id)
            assert group_row is not None

            try:
                conn.execute(
                    """
                    UPDATE feature_choice_option
                    SET
                        name = ?,
                        description = ?,
                        combat_usage_notes = ?,
                        prereq_json = ?,
                        effects_json = ?,
                        display_order = ?
                    WHERE id = ?
                    """,
                    (
                        parsed["name"],
                        parsed["description"],
                        parsed["combat_usage_notes"],
                        parsed["prereq_json"],
                        parsed["effects_json"],
                        parsed["display_order"],
                        option_id,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                msg = str(exc)
                if "UNIQUE constraint failed: feature_choice_option.choice_group_id, feature_choice_option.name" in msg:
                    json_response(
                        self,
                        HTTPStatus.CONFLICT,
                        {"error": "An option with that name already exists in this group."},
                    )
                    return
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": f"Constraint error: {msg}"})
                return

            row = self.choice_option_row_by_id(conn, option_id)

        assert row is not None
        json_response(
            self,
            HTTPStatus.OK,
            {
                "groupId": group_id,
                "classId": int(group_row["class_id"]),
                "option": hydrate_choice_option_row(row),
            },
        )

    def delete_choice_option(self, option_id: int) -> None:
        with connect(self.app_config.db_path) as conn:
            row = conn.execute(
                "SELECT id, choice_group_id FROM feature_choice_option WHERE id = ?",
                (option_id,),
            ).fetchone()
            if row is None:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "Choice option not found"})
                return

            group_id = int(row["choice_group_id"])
            group_row = self.choice_group_row_by_id(conn, group_id)
            assert group_row is not None

            conn.execute("DELETE FROM feature_choice_option WHERE id = ?", (option_id,))
            conn.commit()

        json_response(
            self,
            HTTPStatus.OK,
            {
                "deleted": True,
                "id": option_id,
                "groupId": group_id,
                "classId": int(group_row["class_id"]),
            },
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Character class CRUD spike server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    parser.add_argument(
        "--db",
        default="database/nimble.sqlite",
        help="SQLite database path (default: database/nimble.sqlite)",
    )
    parser.add_argument(
        "--migration",
        default="database/migrations/0001_canonical_schema_freeze.sql",
        help="Migration SQL path used if DB has no tables",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    root = Path.cwd()
    db_path = (root / args.db).resolve()
    migration_path = (root / args.migration).resolve()
    static_dir = (Path(__file__).resolve().parent / "static").resolve()

    if not migration_path.exists():
        raise SystemExit(f"Migration file not found: {migration_path}")
    if not static_dir.exists():
        raise SystemExit(f"Static folder not found: {static_dir}")

    ensure_schema(db_path, migration_path)

    config = AppConfig(db_path=db_path, migration_path=migration_path, static_dir=static_dir)
    server = ThreadingHTTPServer((args.host, args.port), SpikeHandler)
    server.app_config = config  # type: ignore[attr-defined]

    print(
        f"Character class CRUD spike running at http://{args.host}:{args.port} "
        f"(db: {config.db_path})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
