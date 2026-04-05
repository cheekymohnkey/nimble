#!/usr/bin/env python3
"""Validate canonical Nimble rules data (Story 2.5 T5).

Checks:
- SQLite integrity + foreign keys
- uniqueness/no duplicate natural keys
- class/subclass compatibility invariants
- coverage thresholds for required V1 domains
- optional deterministic equality vs another seeded DB
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

EXACT_COUNTS: dict[str, int] = {
    "character_class": 11,
    "skill": 10,
    "language": 10,
}

NON_ZERO_TABLES: tuple[str, ...] = (
    "subclass",
    "ancestry",
    "background",
    "class_level_feature",
    "spell",
)

EXPECTED_STORY_SUBCLASSES: tuple[str, ...] = (
    "Beastmaster",
    "Oathbreaker",
    "Reaver",
    "Spellblade",
)


class ValidationError(RuntimeError):
    """Raised when any validation check fails."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate canonical rules seed outputs")
    parser.add_argument(
        "--db",
        default="database/nimble.sqlite",
        help="SQLite DB path to validate",
    )
    parser.add_argument(
        "--compare-db",
        help="Optional second DB path for deterministic seed equivalence check",
    )
    return parser.parse_args(argv)


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query_int(conn: sqlite3.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def get_user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """,
    ).fetchall()
    return [str(row["name"]) for row in rows]


def assert_integrity(conn: sqlite3.Connection) -> None:
    integrity_rows = conn.execute("PRAGMA integrity_check").fetchall()
    if len(integrity_rows) != 1 or str(integrity_rows[0][0]).lower() != "ok":
        raise ValidationError(f"PRAGMA integrity_check failed: {integrity_rows!r}")

    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_rows:
        raise ValidationError(f"PRAGMA foreign_key_check returned {len(fk_rows)} row(s)")


def assert_no_duplicate_keys(conn: sqlite3.Connection) -> None:
    duplicate_checks: tuple[tuple[str, str], ...] = (
        ("ruleset", "name, version"),
        ("character_class", "ruleset_id, name"),
        ("subclass", "class_id, name"),
        ("ancestry", "ruleset_id, name"),
        ("ancestry_trait", "ancestry_id, name"),
        ("background", "ruleset_id, name"),
        ("background_trait", "background_id, name"),
        ("skill", "name"),
        ("language", "name"),
        ("spell", "ruleset_id, name"),
        ("boon", "ruleset_id, name"),
        ("equipment_item", "ruleset_id, name"),
        ("feature_choice_option", "choice_group_id, name"),
    )
    for table, columns in duplicate_checks:
        dupes = query_int(
            conn,
            f"""
            SELECT COUNT(*) FROM (
              SELECT {columns}, COUNT(*) AS c
              FROM {table}
              GROUP BY {columns}
              HAVING c > 1
            )
            """,
        )
        if dupes != 0:
            raise ValidationError(f"Duplicate natural keys detected in {table} ({columns})")

    class_feature_general_dupes = query_int(
        conn,
        """
        SELECT COUNT(*) FROM (
          SELECT ruleset_id, class_id, level, name, COUNT(*) AS c
          FROM class_level_feature
          WHERE subclass_id IS NULL
          GROUP BY ruleset_id, class_id, level, name
          HAVING c > 1
        )
        """,
    )
    if class_feature_general_dupes != 0:
        raise ValidationError("Duplicate class-level feature keys (general scope) detected")

    class_feature_subclass_dupes = query_int(
        conn,
        """
        SELECT COUNT(*) FROM (
          SELECT ruleset_id, class_id, subclass_id, level, name, COUNT(*) AS c
          FROM class_level_feature
          WHERE subclass_id IS NOT NULL
          GROUP BY ruleset_id, class_id, subclass_id, level, name
          HAVING c > 1
        )
        """,
    )
    if class_feature_subclass_dupes != 0:
        raise ValidationError("Duplicate class-level feature keys (subclass scope) detected")

    group_general_dupes = query_int(
        conn,
        """
        SELECT COUNT(*) FROM (
          SELECT ruleset_id, class_id, name, COUNT(*) AS c
          FROM feature_choice_group
          WHERE subclass_id IS NULL
          GROUP BY ruleset_id, class_id, name
          HAVING c > 1
        )
        """,
    )
    if group_general_dupes != 0:
        raise ValidationError("Duplicate feature choice group keys (general scope) detected")

    group_subclass_dupes = query_int(
        conn,
        """
        SELECT COUNT(*) FROM (
          SELECT ruleset_id, class_id, subclass_id, name, COUNT(*) AS c
          FROM feature_choice_group
          WHERE subclass_id IS NOT NULL
          GROUP BY ruleset_id, class_id, subclass_id, name
          HAVING c > 1
        )
        """,
    )
    if group_subclass_dupes != 0:
        raise ValidationError("Duplicate feature choice group keys (subclass scope) detected")


def assert_class_subclass_compatibility(conn: sqlite3.Connection) -> None:
    mismatch_subclass_parent = query_int(
        conn,
        """
        SELECT COUNT(*)
        FROM subclass s
        JOIN character_class c ON c.id = s.class_id
        WHERE c.ruleset_id != s.ruleset_id
        """,
    )
    if mismatch_subclass_parent != 0:
        raise ValidationError("Subclass rows reference class rows in different rulesets")

    mismatch_feature_scope = query_int(
        conn,
        """
        SELECT COUNT(*)
        FROM class_level_feature f
        JOIN subclass s ON s.id = f.subclass_id
        WHERE f.subclass_id IS NOT NULL
          AND (f.class_id != s.class_id OR f.ruleset_id != s.ruleset_id)
        """,
    )
    if mismatch_feature_scope != 0:
        raise ValidationError("Class-level features have subclass/class scope mismatches")

    mismatch_choice_group_scope = query_int(
        conn,
        """
        SELECT COUNT(*)
        FROM feature_choice_group g
        JOIN subclass s ON s.id = g.subclass_id
        WHERE g.subclass_id IS NOT NULL
          AND (g.class_id != s.class_id OR g.ruleset_id != s.ruleset_id)
        """,
    )
    if mismatch_choice_group_scope != 0:
        raise ValidationError("Feature choice groups have subclass/class scope mismatches")

    story_subclass_count = query_int(
        conn,
        "SELECT COUNT(*) FROM subclass WHERE is_story_based = 1",
    )
    if story_subclass_count != len(EXPECTED_STORY_SUBCLASSES):
        raise ValidationError(
            f"Expected {len(EXPECTED_STORY_SUBCLASSES)} story-based subclasses, got {story_subclass_count}",
        )

    names = [
        str(row["name"])
        for row in conn.execute(
            "SELECT name FROM subclass WHERE is_story_based = 1 ORDER BY name",
        ).fetchall()
    ]
    if tuple(names) != EXPECTED_STORY_SUBCLASSES:
        raise ValidationError(
            f"Story-based subclass names mismatch: expected={EXPECTED_STORY_SUBCLASSES}, got={tuple(names)}",
        )


def gather_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = get_user_tables(conn)
    return {table: query_int(conn, f"SELECT COUNT(*) FROM {table}") for table in tables}


def assert_coverage(counts: dict[str, int]) -> None:
    for table, expected in EXACT_COUNTS.items():
        actual = counts.get(table, 0)
        if actual != expected:
            raise ValidationError(f"Coverage mismatch for {table}: expected={expected}, got={actual}")

    for table in NON_ZERO_TABLES:
        actual = counts.get(table, 0)
        if actual <= 0:
            raise ValidationError(f"Coverage mismatch for {table}: expected > 0, got {actual}")


def table_fingerprint(conn: sqlite3.Connection, table: str) -> str:
    columns = [
        str(row["name"])
        for row in conn.execute(f"PRAGMA table_info({qident(table)})").fetchall()
    ]
    order_by = ", ".join(qident(column) for column in columns)
    rows = conn.execute(f"SELECT * FROM {qident(table)} ORDER BY {order_by}").fetchall()
    payload = {
        "table": table,
        "columns": columns,
        "rows": [[row[column] for column in columns] for row in rows],
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assert_deterministic_equivalence(
    conn_a: sqlite3.Connection,
    conn_b: sqlite3.Connection,
) -> None:
    tables_a = get_user_tables(conn_a)
    tables_b = get_user_tables(conn_b)
    if tables_a != tables_b:
        raise ValidationError(f"Table sets differ between DBs: {tables_a} != {tables_b}")

    for table in tables_a:
        a_hash = table_fingerprint(conn_a, table)
        b_hash = table_fingerprint(conn_b, table)
        if a_hash != b_hash:
            raise ValidationError(f"Deterministic check failed for table {table}: hashes differ")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR DB not found: {db_path}")
        return 1

    try:
        with connect(db_path) as conn:
            assert_integrity(conn)
            assert_no_duplicate_keys(conn)
            assert_class_subclass_compatibility(conn)
            counts = gather_counts(conn)
            assert_coverage(counts)

            if args.compare_db:
                compare_path = Path(args.compare_db)
                if not compare_path.exists():
                    raise ValidationError(f"--compare-db not found: {compare_path}")
                with connect(compare_path) as conn_other:
                    assert_deterministic_equivalence(conn, conn_other)

        print("PASS canonical rules validation")
        for table in sorted(counts):
            print(f"COUNT {table}={counts[table]}")
        if args.compare_db:
            print(f"PASS deterministic equivalence vs {args.compare_db}")
        return 0
    except (sqlite3.Error, OSError, ValueError, ValidationError) as exc:
        print(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
