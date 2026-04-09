#!/usr/bin/env python3
"""Extract a Heroes Core class reference payload from PDF pages.

This script builds importer-compatible JSON in the same shape used by
`*_heroes_core_reference.json` files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


DEFAULT_PDF = (
    "official_books/"
    "Nimble 5e TTRPG Heroes Core Book -- Evan Diaz -- "
    "41845a084350bb7daa48eb313815b1f9 -- Anna’s Archive.pdf"
)
DEFAULT_RULESET = {
    "name": "Nimble 5e 2nd Edition",
    "version": "v1",
    "sourceBook": "Core Rules",
    "sourcePageRef": "All",
}
VALID_FEATURE_TYPES = {
    "auto",
    "choice_grant",
    "resource_change",
    "stat_increase",
    "spell_grant",
    "passive",
    "other",
}


def _import_pypdf() -> Any:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        return PdfReader
    except ModuleNotFoundError:
        sys.path.insert(0, "/tmp/nimble_pdfdeps")
        from pypdf import PdfReader  # type: ignore[import-not-found]

        return PdfReader


def parse_page_spec(spec: str) -> list[int]:
    pages: set[int] = set()
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        if "-" in part:
            a_str, b_str = part.split("-", 1)
            a = int(a_str)
            b = int(b_str)
            lo, hi = (a, b) if a <= b else (b, a)
            pages.update(range(lo, hi + 1))
        else:
            pages.add(int(part))
    if not pages:
        raise ValueError("No pages parsed from --pages")
    return sorted(pages)


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_stat(token: str) -> str:
    token = token.strip().upper().replace("I NT", "INT")
    token = token.replace("WI L", "WIL").replace("DE X", "DEX").replace("ST R", "STR")
    return token


def normalize_name(value: str) -> str:
    text = value.replace("\u2014", " ")
    text = text.replace("\u2013", " ")
    text = normalize_spaces(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


def normalize_feature_name(value: str) -> str:
    text = normalize_spaces(value)
    if text.endswith(".") and not text.endswith("...") and not text.endswith("…"):
        text = text[:-1].rstrip()
    return text


def compact_alnum(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_spaces(value).lower())


def group_heading_compact_keys(name: str) -> set[str]:
    keys: set[str] = set()

    def add_key(value: str) -> None:
        k = compact_alnum(value)
        if k:
            keys.add(k)

    base = normalize_spaces(name)
    base_no_paren = normalize_spaces(re.sub(r"\s*\([^)]*\)\s*", " ", base))
    add_key(base)
    add_key(base_no_paren)

    variants = {base, base_no_paren}
    for value in list(variants):
        lower = value.lower()
        if lower.endswith("ies"):
            variants.add(value[:-3] + "y")
        if lower.endswith("y"):
            variants.add(value[:-1] + "ies")
        if lower.endswith("s"):
            variants.add(value[:-1])
        else:
            variants.add(value + "s")

    for value in variants:
        add_key(value)

    return keys


def normalize_heading_name(value: str) -> str:
    text = normalize_name(value)
    words = text.split()
    out: list[str] = []
    i = 0
    stop_words = {"OF", "THE", "AND", "A", "AN", "TO", "FOR", "IN", "ON", "WITH"}
    while i < len(words):
        word = words[i]
        if word.isalpha() and len(word) <= 2:
            j = i
            run: list[str] = []
            while j < len(words) and words[j].isalpha() and len(words[j]) <= 2:
                run.append(words[j])
                j += 1
            if len(run) >= 2:
                out.append("".join(run))
                i = j
                continue
        if i + 1 < len(words):
            nxt = words[i + 1]
            if (
                word.isalpha()
                and nxt.isalpha()
                and 4 <= len(word) <= 6
                and 1 <= len(nxt) <= 3
                and word not in stop_words
                and nxt not in stop_words
            ):
                out.append(word + nxt)
                i += 2
                continue
        out.append(word)
        i += 1
    return " ".join(out)


def is_subclass_heading_fragment(text: str) -> bool:
    if text.startswith("LEVEL "):
        return False
    if "." in text:
        return False
    if len(text) > 64:
        return False
    if not re.search(r"[\u2013\u2014-]", text):
        return False
    letters_only = re.sub(r"[\u2013\u2014\- ]+", "", text)
    if not letters_only:
        return False
    if any(ch.islower() for ch in letters_only):
        return False
    return True


def load_pdf_pages(pdf_path: Path, pages_1_based: list[int]) -> dict[int, str]:
    PdfReader = _import_pypdf()
    reader = PdfReader(str(pdf_path))
    out: dict[int, str] = {}
    for page in pages_1_based:
        if page < 1 or page > len(reader.pages):
            raise ValueError(f"Requested page {page} outside PDF bounds (1..{len(reader.pages)})")
        out[page] = reader.pages[page - 1].extract_text() or ""
    return out


def split_lines(page_texts: dict[int, str]) -> list[str]:
    lines: list[str] = []
    for page in sorted(page_texts):
        for raw in page_texts[page].splitlines():
            text = normalize_spaces(raw)
            if not text:
                continue
            if re.fullmatch(r"\d+", text):
                continue
            lines.append(text)
    return lines


def parse_class_core(all_text: str, class_name: str) -> dict[str, Any]:
    core: dict[str, Any] = {
        "name": class_name,
        "description": None,
        "hitDie": None,
        "startingHp": None,
        "keyStat1": None,
        "keyStat2": None,
        "saveAdvStat": None,
        "saveDisadvStat": None,
        "armorProficiencies": [],
        "weaponProficiencies": [],
        "startingGear": [],
    }

    stats_match = re.search(
        r"Key Stats:\s*([A-Z]{3})\s*,\s*([A-Z]{3})\b",
        all_text,
        flags=re.IGNORECASE,
    )
    if stats_match:
        core["keyStat1"] = normalize_stat(stats_match.group(1))
        core["keyStat2"] = normalize_stat(stats_match.group(2))

    hit_match = re.search(r"Hit Die:\s*1d(\d+)", all_text, flags=re.IGNORECASE)
    if hit_match:
        core["hitDie"] = int(hit_match.group(1))

    hp_match = re.search(r"Starting HP:\s*(\d+)", all_text, flags=re.IGNORECASE)
    if hp_match:
        core["startingHp"] = int(hp_match.group(1))

    saves_match = re.search(
        r"Saves:\s*([A-Z]{3})\+\s*,\s*([A-Z]{3})[+\-–]?",
        all_text,
        flags=re.IGNORECASE,
    )
    if saves_match:
        core["saveAdvStat"] = normalize_stat(saves_match.group(1))
        core["saveDisadvStat"] = normalize_stat(saves_match.group(2))

    gear_match = re.search(
        r"Armor:\s*(.+?)\s+Weapons:\s*(.+?)\s+Starting Gear:\s*(.+?)(?:\s+LEVEL\s+1|\Z)",
        all_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if gear_match:
        armor = normalize_spaces(gear_match.group(1))
        weapons = normalize_spaces(gear_match.group(2))
        gear = normalize_spaces(gear_match.group(3))
        core["armorProficiencies"] = [part.strip() for part in armor.split(",") if part.strip()]
        core["weaponProficiencies"] = [part.strip() for part in weapons.split(",") if part.strip()]
        core["startingGear"] = [part.strip() for part in gear.split(",") if part.strip()]

    return core


def extract_intro_description(lines: list[str], class_name: str) -> str | None:
    header = normalize_name(class_name)
    header_index: int | None = None
    for idx, line in enumerate(lines):
        if normalize_name(line) == header:
            header_index = idx
            break

    if header_index is None or header_index <= 0:
        return None

    intro_lines = lines[:header_index]
    # Drop-cap PDFs often split the first letter onto its own line.
    if len(intro_lines) >= 2 and re.fullmatch(r"[A-Z]", intro_lines[0]):
        intro_lines = [intro_lines[0] + intro_lines[1], *intro_lines[2:]]

    desc = normalize_spaces(" ".join(intro_lines))
    return desc or None


def infer_feature_type(name: str, description: str | None) -> str:
    joined = f"{name} {description or ''}".lower()
    if "choose" in joined and ("subclass" in joined or "boon" in joined or "ability" in joined):
        return "choice_grant"
    if "spell" in joined and ("unlock" in joined or "tier" in joined or "learn" in joined):
        return "spell_grant"
    if "increase" in joined or "+1" in joined:
        return "stat_increase"
    if "mana" in joined or "resource" in joined or "regain" in joined:
        return "resource_change"
    if "foundation" in joined:
        return "auto"
    return "passive"


def split_name_desc(body: str) -> tuple[str, str | None]:
    multi_bang_trigger_split = re.match(
        r"^(.+![^!]*!)\s+((?:\([^)]*\)\s+)?(?:If|When|Whenever|While|After|Before|On)\b.*)$",
        body,
        flags=re.IGNORECASE,
    )
    if multi_bang_trigger_split:
        return normalize_feature_name(multi_bang_trigger_split.group(1)), normalize_spaces(
            multi_bang_trigger_split.group(2)
        )

    emph_split = re.match(r"^(.+?[!?…])\s+((?:\([^)]*\)\s+)?[A-Z].+)$", body)
    if emph_split:
        return normalize_feature_name(emph_split.group(1)), normalize_spaces(emph_split.group(2))
    trigger_split = re.match(
        r"^(.+?[.!?…])\s+((?:\([^)]*\)\s+)?(?:If|When|Whenever|While|After|Before|On)\b.*)$",
        body,
        flags=re.IGNORECASE,
    )
    if trigger_split:
        return normalize_feature_name(trigger_split.group(1)), normalize_spaces(trigger_split.group(2))
    if ". " in body:
        name, rest = body.split(". ", 1)
        return normalize_feature_name(name), normalize_spaces(rest)
    return normalize_feature_name(body), None


def is_new_feature_line(text: str) -> bool:
    # Standard "<Name>. <Description>" rows.
    if re.match(r"^[A-Z][^.]{1,80}\.\s+", text):
        return True
    # Callout/boxed feature rows, e.g. "Your Rage Ends... If ..." or "Yes! You ..."
    if re.match(r"^[A-Z][A-Za-z0-9'&()/,+ -]{1,80}(?:\.\.\.|…|[!?])\s+", text):
        return True
    return False


def should_repeat_heading_in_description(name: str) -> bool:
    return name.endswith(("...", "…", "!", "?"))


def is_heading_line(line: str) -> bool:
    if line.startswith("("):
        return False
    if line.upper() != line:
        return False
    if line.startswith("LEVEL "):
        return False
    if len(line) > 60:
        return False
    if re.search(r"[a-z]", line):
        return False
    return bool(re.search(r"[A-Z]", line))


def is_plausible_subclass_name(name: str) -> bool:
    text = normalize_spaces(name).upper()
    if len(text) < 6 or len(text) > 48:
        return False
    if any(ch in text for ch in ".,!?():;"):
        return False
    if not re.fullmatch(r"[A-Z0-9 '&/-]+", text):
        return False
    words = text.split()
    return 2 <= len(words) <= 9


def extract_subclass_headers(lines: list[str]) -> list[str]:
    subclasses: list[str] = []
    seen: set[str] = set()
    in_subclasses = False
    pending: str | None = None

    for line in lines:
        text = normalize_spaces(line)
        upper = text.upper()
        if upper == "SUBCLASSES":
            in_subclasses = True
            pending = None
            continue
        if not in_subclasses:
            continue
        if upper.startswith("LEVEL "):
            continue

        if is_subclass_heading_fragment(text):
            cleaned = normalize_heading_name(re.sub(r"[\u2013\u2014-]", " ", text))
            if cleaned:
                # One-line header variant: "— PATH OF THE — MOUNTAINHEART"
                if cleaned not in {"SUBCLASSES"}:
                    if cleaned not in seen and is_plausible_subclass_name(cleaned) and not (
                        cleaned.endswith("OF THE") or cleaned.endswith("OF")
                    ):
                        seen.add(cleaned)
                        subclasses.append(cleaned)
                if cleaned.endswith("OF THE") or cleaned.endswith("OF"):
                    pending = cleaned
            continue

        if pending and is_heading_line(text):
            if upper not in {"SUBCLASSES", "CONTROL TABLE", "CHAOS TABLE"}:
                full = normalize_heading_name(f"{pending} {upper}")
                if full and full not in seen and is_plausible_subclass_name(full):
                    seen.add(full)
                    subclasses.append(full)
            pending = None

    return subclasses


def parse_progression(lines: list[str], subclasses: list[str]) -> list[dict[str, Any]]:
    progression: list[dict[str, Any]] = []
    order_by_scope_level: dict[tuple[str | None, int], int] = {}
    current_level: int | None = None
    current_scope: str | None = None
    in_subclasses = False
    pending_subclass_frag: str | None = None

    def add_feature(level: int, scope: str | None, raw: str) -> None:
        name, desc = split_name_desc(raw)
        if desc and should_repeat_heading_in_description(name):
            desc = normalize_spaces(f"{name} {desc}")
        key = (scope, level)
        order_by_scope_level[key] = order_by_scope_level.get(key, 0) + 1
        feature_type = infer_feature_type(name, desc)
        if feature_type not in VALID_FEATURE_TYPES:
            feature_type = "other"
        progression.append(
            {
                "level": level,
                "scopeSubclass": scope,
                "name": name,
                "featureType": feature_type,
                "displayOrder": order_by_scope_level[key],
                "description": desc,
            }
        )

    for line in lines:
        text = normalize_spaces(line)
        upper = text.upper()
        if upper == "SUBCLASSES":
            in_subclasses = True
            current_level = None
            continue

        if in_subclasses:
            if is_subclass_heading_fragment(text):
                frag = normalize_heading_name(re.sub(r"[\u2013\u2014-]", " ", text))
                if frag:
                    if frag.endswith("OF THE") or frag.endswith("OF"):
                        pending_subclass_frag = frag
                    else:
                        maybe_name = frag
                        if maybe_name in subclasses and is_plausible_subclass_name(maybe_name):
                            current_scope = maybe_name
                continue
            if pending_subclass_frag and is_heading_line(text) and not upper.startswith("LEVEL "):
                maybe_name = normalize_heading_name(f"{pending_subclass_frag} {upper}")
                if maybe_name in subclasses:
                    current_scope = maybe_name
                pending_subclass_frag = None
                continue

        level_match = re.match(r"^LEVEL\s+(\d+)\s+(.+)$", text, flags=re.IGNORECASE)
        if level_match:
            current_level = int(level_match.group(1))
            add_feature(current_level, current_scope if in_subclasses else None, level_match.group(2))
            continue

        if current_level is None:
            continue
        if is_heading_line(text):
            current_level = None
            continue

        is_new_feature = is_new_feature_line(text)
        if is_new_feature:
            add_feature(current_level, current_scope if in_subclasses else None, text)
            continue

        if progression:
            prev = progression[-1]
            if prev.get("description"):
                prev["description"] = f"{prev['description']} {text}"
            else:
                prev["description"] = text

    return progression


def parse_choice_groups(progression: list[dict[str, Any]], subclasses: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str | None, str], dict[str, Any]] = {}
    saw_control_table_reference = False

    def parse_choice_count(text: str) -> int:
        qty_match = re.search(r"\bChoose\s+(\d+)(?:st|nd|rd|th)?\b", text, flags=re.IGNORECASE)
        return int(qty_match.group(1)) if qty_match else 1

    def clean_group_name(raw: str) -> str:
        group_name = normalize_spaces(raw)
        group_name = re.sub(r"^(?:a|an|the)\s+", "", group_name, flags=re.IGNORECASE)
        group_name = re.sub(r"^(?:another|other|next|additional|\d+(?:st|nd|rd|th)?)\s+", "", group_name, flags=re.IGNORECASE)
        group_name = re.sub(r"\s+ability$", "", group_name, flags=re.IGNORECASE)
        group_name = re.sub(
            r"^(?:ability|abilities|option|options)\s+from\s+the\s+",
            "",
            group_name,
            flags=re.IGNORECASE,
        )
        group_name = re.sub(
            r"^(?:ability|abilities|option|options)\s+from\s+",
            "",
            group_name,
            flags=re.IGNORECASE,
        )
        group_name = re.split(r"\s+or\s+", group_name, maxsplit=1, flags=re.IGNORECASE)[0]
        group_name = normalize_spaces(re.sub(r"\s*\([^)]*\)\s*", " ", group_name))
        return group_name

    def infer_group_name_from_feature(feature_name: str) -> str:
        base = normalize_spaces(re.sub(r"\s*\((?:\d+|\d+(?:st|nd|rd|th))\)\s*$", "", feature_name))
        return clean_group_name(base)

    for row in progression:
        desc = row.get("description") or ""
        name = row.get("name") or ""
        combined = normalize_spaces(f"{name}. {desc}")
        scope = row.get("scopeSubclass")

        if re.search(r"\bcontrol table\b", combined, flags=re.IGNORECASE):
            saw_control_table_reference = True

        choose_match = re.search(
            r"\bChoose\s+(\d+(?:st|nd|rd|th)?|an?)\s+(?:additional\s+)?(.+?)(?:\s+abilities?)?(?=[.!;:]|$)",
            combined,
            flags=re.IGNORECASE,
        )
        if choose_match:
            qty_token = choose_match.group(1).lower()
            qty_num = re.match(r"(\d+)", qty_token)
            max_choices = int(qty_num.group(1)) if qty_num else 1
            group_name = clean_group_name(choose_match.group(2))
            if re.search(r"\bepic boon\b", group_name, flags=re.IGNORECASE):
                continue
            if re.search(r"weapon type to specialize in", group_name, flags=re.IGNORECASE):
                group_name = "Weapon Mastery"
            if group_name.lower().endswith("subclass"):
                continue
            lowered_group_name = group_name.lower()
            if lowered_group_name.startswith("option from the") or " table " in f" {lowered_group_name} ":
                continue
            key = (scope, group_name)
            if key not in groups:
                groups[key] = {
                    "scopeSubclass": scope,
                    "name": group_name,
                    "maxChoices": max_choices,
                    "respecRule": "never",
                    "description": None,
                }
            else:
                groups[key]["maxChoices"] = max(groups[key]["maxChoices"], max_choices)

            if "choose different" in desc.lower() and "options available" in desc.lower():
                groups[key]["respecRule"] = "anytime"

        is_counted_choice_grant = bool(
            re.search(
                r"\bChoose\s+(?:\d+(?:st|nd|rd|th)?|an?)\s+(?:additional\s+)?(?:[A-Za-z0-9'()/+\-]+\s+){0,6}(?:ability|abilities|option|options)\b",
                combined,
                flags=re.IGNORECASE,
            )
        )
        lowered = combined.lower()
        if scope is None and is_counted_choice_grant:
            if "epic boon" in lowered:
                continue
            inferred_group_name = infer_group_name_from_feature(name)
            if inferred_group_name and inferred_group_name.lower() not in {"subclass", "key stat increase", "secondary stat increase"}:
                key = (scope, inferred_group_name)
                max_choices = parse_choice_count(combined)
                if key not in groups:
                    groups[key] = {
                        "scopeSubclass": scope,
                        "name": inferred_group_name,
                        "maxChoices": max_choices,
                        "respecRule": "never",
                        "description": None,
                    }
                else:
                    groups[key]["maxChoices"] = max(groups[key]["maxChoices"], max_choices)
                if "choose different" in desc.lower() and "options available" in desc.lower():
                    groups[key]["respecRule"] = "anytime"

        if scope is None and name in subclasses:
            key = (name, name)
            if key not in groups:
                groups[key] = {
                    "scopeSubclass": name,
                    "name": name,
                    "maxChoices": 1,
                    "respecRule": "never",
                    "description": None,
                }

    if saw_control_table_reference:
        control_scope = next((sub for sub in subclasses if "CONTROL" in sub.upper()), None)
        control_key = (control_scope, "Control Table")
        if control_key not in groups:
            groups[control_key] = {
                "scopeSubclass": control_scope,
                "name": "Control Table",
                "maxChoices": 1,
                "respecRule": "never",
                "description": None,
            }

    return list(groups.values())


def parse_choice_options(
    lines: list[str],
    choice_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    group_by_upper: dict[str, dict[str, Any]] = {}
    group_by_compact: dict[str, dict[str, Any]] = {}
    for group in choice_groups:
        group_by_upper[normalize_name(group["name"])] = group
        for key in group_heading_compact_keys(group["name"]):
            group_by_compact[key] = group

    out: list[dict[str, Any]] = []
    current_group: dict[str, Any] | None = None
    current_option: dict[str, Any] | None = None
    display_order_by_group: dict[tuple[str | None, str], int] = {}
    pending_heading_line: str | None = None
    weapon_mastery_names = {"Slashing", "Bludgeoning", "Piercing"}
    ocr_wrap_fragments = {"Combat Die", "Medium Armor"}

    def find_matching_group(scope: str | None, desired_name: str) -> dict[str, Any] | None:
        for group in choice_groups:
            if group.get("scopeSubclass") == scope and normalize_name(group["name"]) == normalize_name(desired_name):
                return group
        return None

    for line in lines:
        text = normalize_spaces(line)
        upper = normalize_name(text)
        compact = compact_alnum(text)

        if upper in group_by_upper:
            current_group = group_by_upper[upper]
            current_option = None
            pending_heading_line = None
            continue
        if compact and compact in group_by_compact:
            current_group = group_by_compact[compact]
            current_option = None
            pending_heading_line = None
            continue
        if current_group is None and is_heading_line(text):
            combined = normalize_spaces(f"{pending_heading_line} {text}") if pending_heading_line else text
            combined_compact = compact_alnum(combined)
            if combined_compact in group_by_compact:
                current_group = group_by_compact[combined_compact]
                current_option = None
                pending_heading_line = None
                continue
            pending_heading_line = text
            continue
        pending_heading_line = None

        if current_group is None:
            continue
        if upper in {"SUBCLASSES", "CONTROL TABLE", "CHAOS TABLE"} or is_heading_line(text):
            current_group = None
            current_option = None
            pending_heading_line = None
            continue
        if text.startswith("LEVEL "):
            current_group = None
            current_option = None
            pending_heading_line = None
            continue
        lowered = text.lower()
        if current_option is not None and "choose different" in lowered and "options available" in lowered:
            if out and out[-1] is current_option:
                out.pop()
            current_group = None
            current_option = None
            pending_heading_line = None
            continue
        if "choose different" in lowered and "options available" in lowered:
            current_group = None
            current_option = None
            pending_heading_line = None
            continue

        option_match = re.match(r"^([A-Z][A-Za-z0-9'!()/ -]{1,80})\.\s*(.*)$", text)
        if not option_match:
            option_match = re.match(r"^([A-Z][A-Za-z0-9'’&()/,+ -]{1,80}[!?…])\s*(.*)$", text)
        if option_match:
            name = normalize_spaces(option_match.group(1))
            desc = normalize_spaces(option_match.group(2))
            if current_option is not None and name in ocr_wrap_fragments:
                fragment = f"{name}. {desc}" if desc else name
                current_option["description"] = normalize_spaces(
                    f"{current_option.get('description') or ''} {fragment}"
                )
                continue
            word_count = len(name.split())
            if not desc and word_count == 1:
                if current_option is not None:
                    current_option["description"] = normalize_spaces(
                        f"{current_option.get('description') or ''} {name}"
                    )
                continue
            if word_count > 6:
                current_option = None
                continue
            lname = name.lower()
            if lname.startswith("gain ") or lname.startswith("where's the "):
                current_option = None
                continue
            if "choose different" in desc.lower() and "options available" in desc.lower():
                current_option = None
                continue
            target_group = current_group
            if current_group["name"] == "Combat Tactic" and name in weapon_mastery_names:
                maybe_weapon_mastery = find_matching_group(current_group.get("scopeSubclass"), "Weapon Mastery")
                if maybe_weapon_mastery is not None:
                    target_group = maybe_weapon_mastery

            gkey = (target_group.get("scopeSubclass"), target_group["name"])
            display_order_by_group[gkey] = display_order_by_group.get(gkey, 0) + 1
            current_option = {
                "groupName": target_group["name"],
                "scopeSubclass": target_group.get("scopeSubclass"),
                "name": name,
                "description": desc or None,
                "prereq": {},
                "effects": {},
                "displayOrder": display_order_by_group[gkey],
            }
            out.append(current_option)
            continue

        if current_option is not None:
            extra = normalize_spaces(text)
            if extra:
                if current_option["description"]:
                    current_option["description"] = f"{current_option['description']} {extra}"
                else:
                    current_option["description"] = extra

    return out


def slugify_feature(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def augment_subclass_choice_entries(
    subclasses: list[dict[str, Any]],
    progression: list[dict[str, Any]],
    choice_groups: list[dict[str, Any]],
    choice_options: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    subclass_names = [row["name"] for row in subclasses]
    sub_rows: dict[str, list[dict[str, Any]]] = {
        name: [row for row in progression if row.get("scopeSubclass") == name]
        for name in subclass_names
    }

    existing_group_keys = {(row.get("scopeSubclass"), row["name"]) for row in choice_groups}
    for name in subclass_names:
        key = (name, name)
        if key in existing_group_keys:
            continue
        rows = sub_rows.get(name, [])
        if not rows:
            continue
        choice_groups.append(
            {
                "scopeSubclass": name,
                "name": name,
                "maxChoices": len(rows),
                "respecRule": "never",
                "description": None,
            }
        )

    non_subclass_options = [row for row in choice_options if not row.get("scopeSubclass")]
    subclass_option_map: dict[tuple[str, str], dict[str, Any]] = {}
    for row in choice_options:
        scope = row.get("scopeSubclass")
        if scope:
            subclass_option_map[(scope, row["name"])] = row

    for scope in subclass_names:
        rows = sorted(
            sub_rows.get(scope, []),
            key=lambda row: (int(row.get("level", 0)), int(row.get("displayOrder", 0)), row.get("name", "")),
        )
        for idx, row in enumerate(rows):
            key = (scope, row["name"])
            subclass_option_map[key] = {
                "groupName": scope,
                "scopeSubclass": scope,
                "name": row["name"],
                "description": row.get("description"),
                "prereq": {"level": int(row["level"])},
                "effects": [{"type": "subclass_feature", "slug": slugify_feature(row["name"])}],
                "displayOrder": idx,
            }

    ordered_subclass_options: list[dict[str, Any]] = []
    for scope in subclass_names:
        rows = [
            row
            for (scope_name, _), row in subclass_option_map.items()
            if scope_name == scope
        ]
        rows = sorted(
            rows,
            key=lambda row: (int(row.get("prereq", {}).get("level", 0)), row.get("displayOrder", 0), row["name"]),
        )
        for idx, row in enumerate(rows):
            row["displayOrder"] = idx
            ordered_subclass_options.append(row)

    return choice_groups, non_subclass_options + ordered_subclass_options


def validate_extracted_payload(payload: dict[str, Any]) -> None:
    required_keys = {"source", "ruleset", "class", "subclasses", "progression", "choiceGroups", "choiceOptions"}
    missing = required_keys - set(payload.keys())
    if missing:
        raise RuntimeError(f"Payload missing keys: {sorted(missing)}")

    cls = payload["class"]
    for key in ("name", "hitDie", "startingHp", "keyStat1", "keyStat2", "saveAdvStat", "saveDisadvStat"):
        if cls.get(key) in (None, "", []):
            raise RuntimeError(f"Class field missing/empty: {key}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract Heroes Core class reference JSON from PDF pages")
    parser.add_argument("--class-name", required=True, help="Class name, e.g. 'Mage'")
    parser.add_argument(
        "--pages",
        required=True,
        help="Page spec, e.g. '32-36' or '32,33,34,35,36'",
    )
    parser.add_argument("--pdf", default=DEFAULT_PDF, help="Heroes Core PDF path")
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: database/seed_data/v1/<class>_heroes_core_reference.json)",
    )
    parser.add_argument(
        "--dump-text",
        default=None,
        help="Optional path to dump concatenated extracted text",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    class_name = normalize_spaces(args.class_name)
    pages = parse_page_spec(args.pages)
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path("database/seed_data/v1") / f"{slugify(class_name)}_heroes_core_reference.json"

    page_texts = load_pdf_pages(pdf_path, pages)
    lines = split_lines(page_texts)
    all_text = "\n".join(lines)

    cls = parse_class_core(all_text, class_name)
    cls["description"] = extract_intro_description(lines, class_name)
    subclasses = [{"name": name, "isStoryBased": False, "description": None} for name in extract_subclass_headers(lines)]
    progression = parse_progression(lines, [s["name"] for s in subclasses])
    choice_groups = parse_choice_groups(progression, [s["name"] for s in subclasses])
    choice_options = parse_choice_options(lines, choice_groups)
    choice_groups, choice_options = augment_subclass_choice_entries(
        subclasses,
        progression,
        choice_groups,
        choice_options,
    )

    payload = {
        "source": {
            "pdf": str(pdf_path),
            "pages": pages,
        },
        "ruleset": dict(DEFAULT_RULESET),
        "class": cls,
        "subclasses": subclasses,
        "progression": progression,
        "choiceGroups": choice_groups,
        "choiceOptions": choice_options,
    }
    validate_extracted_payload(payload)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.dump_text:
        Path(args.dump_text).write_text(all_text + "\n", encoding="utf-8")

    print(f"Wrote {out_path}")
    print(
        "Extracted "
        f"class={payload['class']['name']} "
        f"subclasses={len(subclasses)} progression={len(progression)} "
        f"groups={len(choice_groups)} options={len(choice_options)}"
    )


if __name__ == "__main__":
    main()
