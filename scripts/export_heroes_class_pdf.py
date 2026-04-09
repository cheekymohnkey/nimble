#!/usr/bin/env python3
"""Export Heroes Core class reference JSON to a styled PDF.

This exporter renders a print-friendly, Heroes-inspired layout from
`*_heroes_core_reference.json` files produced by the extraction pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _import_reportlab() -> tuple[Any, Any, Any, Any, Any, Any]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        return (
            colors,
            TA_CENTER,
            LETTER,
            ParagraphStyle,
            getSampleStyleSheet,
            (Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle),
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency 'reportlab'. Install it with: "
            "pip install reportlab"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a Heroes Core class reference payload to PDF",
    )
    parser.add_argument(
        "--reference",
        required=True,
        help="Path to *_heroes_core_reference.json",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output PDF path (default: same folder as reference, class slug + _layout.pdf)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional override title for the PDF cover heading",
    )
    return parser.parse_args()


def load_reference(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Reference payload not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"class", "subclasses", "progression", "choiceGroups", "choiceOptions", "ruleset", "source"}
    missing = required - set(payload.keys())
    if missing:
        raise SystemExit(f"Reference payload missing keys: {sorted(missing)}")
    return payload


def p(text: str) -> str:
    """Minimal XML escaping for reportlab Paragraph strings."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_pdf(reference: dict[str, Any], out_path: Path, title_override: str | None) -> None:
    colors, ta_center, letter, paragraph_style, get_styles, platypus = _import_reportlab()
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle = platypus

    styles = get_styles()
    title_style = paragraph_style(
        "HeroesTitle",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=28,
        leading=32,
        alignment=ta_center,
        textColor=colors.HexColor("#2B1D12"),
        spaceAfter=10,
    )
    subtitle_style = paragraph_style(
        "HeroesSubtitle",
        parent=styles["Normal"],
        fontName="Times-Italic",
        fontSize=11,
        leading=14,
        alignment=ta_center,
        textColor=colors.HexColor("#4D4036"),
        spaceAfter=14,
    )
    section_style = paragraph_style(
        "HeroesSection",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#3B281B"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = paragraph_style(
        "HeroesBody",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#221A14"),
    )
    small_style = paragraph_style(
        "HeroesSmall",
        parent=styles["Normal"],
        fontName="Times-Italic",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#55463B"),
    )

    cls = reference["class"]
    ruleset = reference["ruleset"]
    source = reference["source"]

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        topMargin=36,
        bottomMargin=36,
        leftMargin=42,
        rightMargin=42,
        title=f"{cls['name']} - Heroes Class Layout",
        author="nimble exporter",
    )

    story: list[Any] = []
    title = title_override or f"{cls['name']}"
    story.append(Paragraph(p(title), title_style))

    pages_text = ", ".join(str(page) for page in source.get("pages", []))
    source_line = (
        f"{ruleset.get('name', '')} {ruleset.get('version', '')}"
        f" - Source pages: {pages_text}"
    )
    story.append(Paragraph(p(source_line), subtitle_style))

    story.append(Paragraph("Class Profile", section_style))
    stats_rows = [
        ["Hit Die", f"1d{cls.get('hitDie', '-')}", "Starting HP", str(cls.get("startingHp", "-"))],
        ["Key Stats", f"{cls.get('keyStat1', '-')}, {cls.get('keyStat2', '-')}", "Saves", f"{cls.get('saveAdvStat', '-') }+, {cls.get('saveDisadvStat', '-') }"],
        ["Armor", ", ".join(cls.get("armorProficiencies", [])) or "-", "Weapons", ", ".join(cls.get("weaponProficiencies", [])) or "-"],
    ]
    stats_table = Table(stats_rows, colWidths=[70, 170, 70, 190])
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F1EA")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#8C765F")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7B7A7")),
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(stats_table)
    story.append(Spacer(1, 8))

    starting_gear = ", ".join(cls.get("startingGear", [])) or "-"
    story.append(Paragraph(f"<b>Starting Gear:</b> {p(starting_gear)}", body_style))
    story.append(Spacer(1, 8))
    if cls.get("description"):
        story.append(Paragraph(p(cls["description"]), body_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Level Progression", section_style))

    progression_rows = [["Lvl", "Scope", "Feature", "Type", "Description"]]
    for row in sorted(
        reference["progression"],
        key=lambda r: (int(r.get("level", 0)), r.get("scopeSubclass") or "", int(r.get("displayOrder", 0))),
    ):
        progression_rows.append(
            [
                str(row.get("level", "")),
                row.get("scopeSubclass") or "Core",
                row.get("name") or "",
                row.get("featureType") or "",
                row.get("description") or "",
            ]
        )

    progression_table = Table(progression_rows, colWidths=[28, 102, 120, 64, 186], repeatRows=1)
    progression_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9DED1")),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#8C765F")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBBEAF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(progression_table)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Option Groups", section_style))

    options_by_group: dict[tuple[str | None, str], list[dict[str, Any]]] = {}
    for option in reference["choiceOptions"]:
        key = (option.get("scopeSubclass"), option.get("groupName"))
        options_by_group.setdefault(key, []).append(option)

    for group in reference["choiceGroups"]:
        scope = group.get("scopeSubclass")
        group_name = group.get("name")
        scope_label = scope or "Core"
        group_title = f"{scope_label} - {group_name} (max choices: {group.get('maxChoices', 1)})"
        story.append(Paragraph(p(group_title), paragraph_style(
            "GroupHeading",
            parent=styles["Heading3"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#3B2E22"),
            spaceBefore=6,
            spaceAfter=3,
        )))
        group_options = sorted(
            options_by_group.get((scope, group_name), []),
            key=lambda o: int(o.get("displayOrder", 0)),
        )
        if not group_options:
            story.append(Paragraph("No options extracted for this group.", small_style))
            continue
        for option in group_options:
            opt_name = option.get("name") or "(unnamed option)"
            opt_desc = option.get("description") or ""
            story.append(Paragraph(f"<b>{p(opt_name)}.</b> {p(opt_desc)}", body_style))
        story.append(Spacer(1, 6))

    if reference["subclasses"]:
        story.append(Paragraph("Subclasses", section_style))
        subclass_names = [row.get("name") for row in reference["subclasses"] if row.get("name")]
        story.append(Paragraph(p(" - ".join(subclass_names)), body_style))

    doc.build(story)


def main() -> None:
    args = parse_args()
    ref_path = Path(args.reference)
    reference = load_reference(ref_path)

    if args.out:
        out_path = Path(args.out)
    else:
        cls_name = str(reference["class"]["name"]).lower().replace(" ", "_")
        out_path = ref_path.with_name(f"{cls_name}_heroes_layout.pdf")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(reference, out_path, args.title)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
