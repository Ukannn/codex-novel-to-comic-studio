"""Build half-manual page-level image-generation task sheets from storyboard JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import read_json, write_json
from .config import ProductionSettings


def build_image_tasks(
    storyboard_path: str | Path,
    visual_bible_dir: str | Path,
    chapter_id: str,
    *,
    settings: ProductionSettings | None = None,
) -> list[dict[str, Any]]:
    production = settings if settings is not None else ProductionSettings()
    storyboard_file = Path(storyboard_path)
    visual_root = Path(visual_bible_dir)
    storyboard = read_json(storyboard_file)
    tasks: list[dict[str, Any]] = []

    for page in storyboard.get("pages", []):
        page_number = int(page["page"])
        layout = page.get("layout", "story-led full-page manga layout")
        panels = page.get("panels", [])
        references = _references_for_page(panels, visual_root)
        tasks.append(
            {
                "chapter": chapter_id,
                "page": page_number,
                "panel_count": len(panels),
                "target": f"chapters/{chapter_id}/finished-pages/page-{page_number:03d}.png",
                "target_size_px": {"width": production.page_size[0], "height": production.page_size[1]},
                "minimum_short_edge_px": production.minimum_short_edge_px,
                "trim_size": production.trim_size,
                "layout": layout,
                "references": references,
                "prompt": _prompt_for_page(page, layout, production),
            }
        )

    return tasks


def write_image_tasks(tasks: list[dict[str, Any]], output_path: str | Path) -> None:
    write_json(output_path, tasks)


def _references_for_page(panels: list[dict[str, Any]], visual_root: Path) -> list[dict[str, str]]:
    seen: set[str] = set()
    references: list[dict[str, str]] = []
    for panel in panels:
        for reference in _references_for_panel(panel, visual_root):
            path = reference["path"]
            if path in seen:
                continue
            references.append(reference)
            seen.add(path)
    return references[:10]


def _prompt_for_page(page: dict[str, Any], layout: str, settings: ProductionSettings) -> str:
    panel_lines: list[str] = []
    text_lines: list[str] = []
    for panel in page.get("panels", []):
        panel_number = panel.get("panel", "?")
        shot = panel.get("shot", "medium")
        angle = panel.get("angle", "eye")
        description = panel.get("description", "")
        chars = ", ".join(char.get("id", "") for char in panel.get("chars", []) if char.get("id")) or "no named characters"
        panel_lines.append(
            f"Panel {panel_number}: {shot} shot, {angle} angle. {description} Characters: {chars}."
        )
        for caption in panel.get("captions", []):
            if caption.get("text"):
                text_lines.append(f"Panel {panel_number} caption: {caption['text']}")
        for dialogue in panel.get("dialogue", []):
            if dialogue.get("text"):
                speaker = dialogue.get("speaker", "speaker")
                text_lines.append(f"Panel {panel_number} {speaker}: {dialogue['text']}")
        for sfx in panel.get("sfx", []):
            if sfx.get("text"):
                text_lines.append(f"Panel {panel_number} SFX: {sfx['text']}")

    joined_panels = " ".join(panel_lines)
    joined_text = " ".join(text_lines) if text_lines else "No required reader text on this page."
    language = {
        "zh": "Chinese", "zh-CN": "Chinese", "zh-Hans": "Chinese",
        "zh-TW": "Traditional Chinese", "zh-Hant": "Traditional Chinese",
        "en": "English", "ko": "Korean", "ja": "Japanese",
    }.get(settings.target_language, settings.target_language)
    width, height = settings.page_size
    return (
        f"Generate one complete readable finished manga page in {settings.trim_size} portrait, final production target {width}x{height} px or higher, "
        f"minimum short edge {settings.minimum_short_edge_px} px. Use the layout intent: {layout}. "
        f"Page content: {joined_panels} "
        f"Exact {language} reader text to render cleanly in balloons, captions, and SFX: {joined_text} "
        "Use supplied references for identity, wardrobe, and setting consistency across all panels on the page. "
        "Keep all text inside safe areas, avoid covering faces, hands, weapons, and key action, and do not add extra random glyphs, signatures, subtitles, or watermarks."
    )


def _references_for_panel(panel: dict[str, Any], visual_root: Path) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    for char in panel.get("chars", []):
        char_id = char.get("id")
        if not char_id:
            continue
        char_root = visual_root / "characters" / char_id
        reference_card = char_root / "reference-card.png"
        if reference_card.exists():
            references.append({"path": str(reference_card), "role": f"{char_id} approved character reference card"})
            continue
        references.append({"path": str(char_root / "face-canonical.png"), "role": f"{char_id} canonical face"})
        outfit = char.get("outfit", "default")
        references.append({"path": str(char_root / "wardrobe" / outfit / "turnaround-front.png"), "role": f"{char_id} outfit {outfit}"})
        expression = char.get("expression")
        if expression:
            references.append({"path": str(char_root / "expressions" / f"{expression}.png"), "role": f"{char_id} expression {expression}"})

    setting_id = panel.get("setting")
    if setting_id:
        shot = panel.get("shot", "wide")
        setting_time = panel.get("setting_time", "day")
        references.append({"path": str(visual_root / "settings" / setting_id / f"{shot}-{setting_time}.png"), "role": f"{setting_id} setting"})

    return references[:6]
