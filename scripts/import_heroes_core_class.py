#!/usr/bin/env python3
"""Import a class from a Heroes Core reference payload into SQLite.

The reference payload is class-scoped and deterministic: existing rows for that
class are replaced during import so reruns produce stable output.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Any


DEFAULT_PDF = (
    "official_books/"
    "Nimble 5e TTRPG Heroes Core Book -- Evan Diaz -- "
    "41845a084350bb7daa48eb313815b1f9 -- Anna’s Archive.pdf"
)
DEFAULT_REFERENCE = "database/seed_data/v1/berserker_heroes_core_reference.json"


def _import_pypdf() -> Any:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        return PdfReader
    except ModuleNotFoundError:
        # Session-local dependency location used in this workspace.
        sys.path.insert(0, "/tmp/nimble_pdfdeps")
        from pypdf import PdfReader  # type: ignore[import-not-found]

        return PdfReader


def normalize_for_match(value: str) -> str:
    text = value.replace("-\n", "")
    text = text.replace("\n", " ")
    text = text.replace("’", "'").replace("–", "-").replace("—", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9+!()'/-]+", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_pdf_text(pdf_path: Path, pages_1_based: list[int]) -> str:
    PdfReader = _import_pypdf()
    reader = PdfReader(str(pdf_path))
    extracted: list[str] = []
    for page in pages_1_based:
        if page < 1 or page > len(reader.pages):
            raise ValueError(f"Requested page {page} outside PDF bounds (1..{len(reader.pages)})")
        extracted.append(reader.pages[page - 1].extract_text() or "")
    return "\n".join(extracted)


def ensure_reference_shape(reference: dict[str, Any]) -> None:
    required = ["ruleset", "class", "subclasses", "progression", "choiceGroups", "choiceOptions"]
    missing = [key for key in required if key not in reference]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Reference JSON missing required key(s): {joined}")


def collect_anchors(reference: dict[str, Any]) -> list[str]:
    cls = reference["class"]
    anchors = [
        cls["name"],
        f"Key Stats: {cls['keyStat1']}, {cls['keyStat2']}",
        f"Hit Die: 1d{int(cls['hitDie'])}",
        f"Starting HP: {int(cls['startingHp'])}",
        f"Saves: {cls['saveAdvStat']}+, {cls['saveDisadvStat']}",
    ]

    for row in reference["subclasses"]:
        anchors.append(row["name"])
    for row in reference["progression"]:
        anchors.append(row["name"])
    for row in reference["choiceGroups"]:
        anchors.append(row["name"])
    for row in reference["choiceOptions"]:
        anchors.append(row["name"])

    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in anchors:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def validate_reference_against_pdf(reference: dict[str, Any], pdf_text: str) -> None:
    haystack = normalize_for_match(pdf_text)
    missing: list[str] = []
    for anchor in collect_anchors(reference):
        needle = normalize_for_match(anchor)
        if needle and needle not in haystack:
            missing.append(anchor)
    if missing:
        sample = ", ".join(missing[:12])
        raise RuntimeError(
            f"PDF validation failed. Missing {len(missing)} anchor(s), e.g.: {sample}",
        )


def to_json_text(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def ensure_ruleset(conn: sqlite3.Connection, ruleset: dict[str, Any]) -> int:
    row = conn.execute(
        "SELECT id FROM ruleset WHERE name = ? AND version = ?",
        (ruleset["name"], ruleset["version"]),
    ).fetchone()
    if row is not None:
        rid = int(row["id"])
        conn.execute(
            """
            UPDATE ruleset
            SET source_book = ?, source_page_ref = ?
            WHERE id = ?
            """,
            (
                ruleset.get("sourceBook"),
                ruleset.get("sourcePageRef"),
                rid,
            ),
        )
        return rid

    cur = conn.execute(
        """
        INSERT INTO ruleset (name, version, source_book, source_page_ref)
        VALUES (?, ?, ?, ?)
        """,
        (
            ruleset["name"],
            ruleset["version"],
            ruleset.get("sourceBook"),
            ruleset.get("sourcePageRef"),
        ),
    )
    return int(cur.lastrowid)


def ensure_optional_columns(conn: sqlite3.Connection) -> None:
    tables = ("class_level_feature", "feature_choice_option")
    table_columns: dict[str, set[str]] = {}
    for table in tables:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        table_columns[table] = {str(row["name"]) for row in rows}

    if "combat_usage_notes" not in table_columns["class_level_feature"]:
        conn.execute("ALTER TABLE class_level_feature ADD COLUMN combat_usage_notes TEXT")
    if "combat_usage_notes" not in table_columns["feature_choice_option"]:
        conn.execute("ALTER TABLE feature_choice_option ADD COLUMN combat_usage_notes TEXT")


def upsert_class_from_reference(
    conn: sqlite3.Connection,
    reference: dict[str, Any],
    ruleset_id: int,
) -> dict[str, int]:
    cls = reference["class"]
    row = conn.execute(
        "SELECT id FROM character_class WHERE ruleset_id = ? AND name = ?",
        (ruleset_id, cls["name"]),
    ).fetchone()
    if row is None:
        cur = conn.execute(
            """
            INSERT INTO character_class (
                ruleset_id, name, description, hit_die, starting_hp,
                key_stat_1, key_stat_2, save_adv_stat, save_disadv_stat,
                armor_proficiencies_json, weapon_proficiencies_json, starting_gear_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ruleset_id,
                cls["name"],
                cls.get("description"),
                int(cls["hitDie"]),
                int(cls["startingHp"]),
                cls["keyStat1"],
                cls["keyStat2"],
                cls["saveAdvStat"],
                cls["saveDisadvStat"],
                to_json_text(cls.get("armorProficiencies", [])),
                to_json_text(cls.get("weaponProficiencies", [])),
                to_json_text(cls.get("startingGear", [])),
            ),
        )
        class_id = int(cur.lastrowid)
    else:
        class_id = int(row["id"])
        conn.execute(
            """
            UPDATE character_class
            SET
                description = ?, hit_die = ?, starting_hp = ?,
                key_stat_1 = ?, key_stat_2 = ?, save_adv_stat = ?, save_disadv_stat = ?,
                armor_proficiencies_json = ?, weapon_proficiencies_json = ?, starting_gear_json = ?
            WHERE id = ?
            """,
            (
                cls.get("description"),
                int(cls["hitDie"]),
                int(cls["startingHp"]),
                cls["keyStat1"],
                cls["keyStat2"],
                cls["saveAdvStat"],
                cls["saveDisadvStat"],
                to_json_text(cls.get("armorProficiencies", [])),
                to_json_text(cls.get("weaponProficiencies", [])),
                to_json_text(cls.get("startingGear", [])),
                class_id,
            ),
        )

    # Replace class-scoped rows so importer output stays deterministic.
    conn.execute("DELETE FROM class_level_feature WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM feature_choice_group WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM subclass WHERE class_id = ?", (class_id,))

    subclass_ids: dict[str, int] = {}
    for row in reference["subclasses"]:
        cur = conn.execute(
            """
            INSERT INTO subclass (ruleset_id, class_id, name, is_story_based, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ruleset_id,
                class_id,
                row["name"],
                1 if row.get("isStoryBased") else 0,
                row.get("description"),
            ),
        )
        subclass_ids[row["name"]] = int(cur.lastrowid)

    for row in reference["progression"]:
        scope = row.get("scopeSubclass")
        subclass_id = subclass_ids.get(scope) if scope else None
        conn.execute(
            """
            INSERT INTO class_level_feature (
                ruleset_id, class_id, subclass_id, level, name, description, combat_usage_notes,
                feature_type, display_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ruleset_id,
                class_id,
                subclass_id,
                int(row["level"]),
                row["name"],
                row.get("description"),
                row.get("combatUsageNotes"),
                row["featureType"],
                int(row.get("displayOrder", 0)),
            ),
        )

    group_ids: dict[tuple[str | None, str], int] = {}
    for row in reference["choiceGroups"]:
        scope = row.get("scopeSubclass")
        subclass_id = subclass_ids.get(scope) if scope else None
        cur = conn.execute(
            """
            INSERT INTO feature_choice_group (
                ruleset_id, class_id, subclass_id, name, max_choices, respec_rule, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ruleset_id,
                class_id,
                subclass_id,
                row["name"],
                int(row["maxChoices"]),
                row["respecRule"],
                row.get("description"),
            ),
        )
        group_ids[(scope, row["name"])] = int(cur.lastrowid)

    for row in reference["choiceOptions"]:
        group_id = group_ids[(row.get("scopeSubclass"), row["groupName"])]
        conn.execute(
            """
            INSERT INTO feature_choice_option (
                choice_group_id, name, description, combat_usage_notes,
                prereq_json, effects_json, display_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group_id,
                row["name"],
                row.get("description"),
                row.get("combatUsageNotes"),
                to_json_text(row.get("prereq")),
                to_json_text(row.get("effects")),
                int(row.get("displayOrder", 0)),
            ),
        )

    return {
        "classId": class_id,
        "subclasses": len(subclass_ids),
        "progression": len(reference["progression"]),
        "choiceGroups": len(reference["choiceGroups"]),
        "choiceOptions": len(reference["choiceOptions"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import class data from a Heroes Core reference payload")
    parser.add_argument("--db", required=True, help="SQLite DB path")
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Heroes Core PDF path")
    parser.add_argument("--reference", default=DEFAULT_REFERENCE, help="Reference JSON payload path")
    parser.add_argument(
        "--skip-pdf-validation",
        action="store_true",
        help="Skip text-anchor validation against the PDF before importing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    pdf_path = Path(args.pdf)
    ref_path = Path(args.reference)

    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")
    if not ref_path.exists():
        raise SystemExit(f"Reference payload not found: {ref_path}")
    if not args.skip_pdf_validation and not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    reference = json.loads(ref_path.read_text(encoding="utf-8"))
    ensure_reference_shape(reference)

    if not args.skip_pdf_validation:
        source = reference.get("source", {})
        pages = source.get("pages")
        if not isinstance(pages, list) or not pages:
            raise RuntimeError("Reference JSON must include source.pages for PDF validation")
        pdf_text = load_pdf_text(pdf_path, [int(p) for p in pages])
        validate_reference_against_pdf(reference, pdf_text)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_optional_columns(conn)
        ruleset_id = ensure_ruleset(conn, reference["ruleset"])
        stats = upsert_class_from_reference(conn, reference, ruleset_id)
        conn.commit()

    class_name = reference["class"]["name"]
    print(
        f"Imported {class_name} from Heroes Core reference "
        f"(class_id={stats['classId']}, subclasses={stats['subclasses']}, "
        f"progression={stats['progression']}, groups={stats['choiceGroups']}, "
        f"options={stats['choiceOptions']}).",
    )


if __name__ == "__main__":
    main()
