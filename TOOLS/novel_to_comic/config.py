"""Configuration loading and validation for novel-to-comic projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import read_json


SUPPORTED_FORMATS = ["txt", "epub"]
TRIM_SIZES = {"B5", "A4", "manga-standard"}
COMPRESSION_MODES = {"essence", "standard", "complete"}
APPROVAL_MODES = {"chapter", "every_n_chapters", "auto_after_first"}
PROJECT_MODES = {"private_experiment", "licensed_commercial", "public_domain"}
TARGET_FORMATS = {"manga_page", "color_comic", "webtoon", "storyboard_only"}
AUTOMATION_LEVELS = {1, 2, 3}
PAGE_COUNT_POLICIES = {"story_first_variable", "fixed_budget", "soft_target"}
FINISHED_PAGE_TEXT_MODES = {"image2_embedded", "deterministic_lettering_fallback"}

# Standalone tool defaults. Project choices come from an explicitly supplied
# preferences file; importing this module never reads project files.
DEFAULT_PAGE_SIZE = (2480, 3508)
DEFAULT_MINIMUM_SHORT_EDGE_PX = 2048
DEFAULT_TRIM_SIZE = "A4"
DEFAULT_PANEL_GUTTER_PX = 8
DEFAULT_TARGET_LANGUAGE = "zh-CN"


@dataclass(frozen=True)
class ProductionSettings:
    """Resolved values consumed by task generation, rendering and QC."""

    page_size: tuple[int, int] = DEFAULT_PAGE_SIZE
    minimum_short_edge_px: int = DEFAULT_MINIMUM_SHORT_EDGE_PX
    trim_size: str = DEFAULT_TRIM_SIZE
    target_language: str = DEFAULT_TARGET_LANGUAGE
    panel_gutter_px: int = DEFAULT_PANEL_GUTTER_PX

    def page_size_with_overrides(
        self, width: int | None = None, height: int | None = None,
    ) -> tuple[int, int]:
        """Apply explicit CLI dimensions, including small preview canvases."""
        size = (
            self.page_size[0] if width is None else width,
            self.page_size[1] if height is None else height,
        )
        if any(type(edge) is not int or edge < 1 for edge in size):
            raise ValueError("page width and height must be positive integers")
        return size


def load_production_settings(path: str | Path | None = None) -> ProductionSettings:
    """Resolve an explicit project file, or retain legacy standalone defaults."""
    if path is None:
        return ProductionSettings()
    preferences = load_preferences(path)
    errors = validate_preferences(preferences)
    if errors:
        raise ValueError("Invalid preferences: " + "; ".join(errors))
    comic = preferences["comic"]
    size = comic["page_size_px"]
    return ProductionSettings(
        page_size=(size["width"], size["height"]),
        minimum_short_edge_px=comic["minimum_short_edge_px"],
        trim_size=comic["trim_size"],
        target_language=preferences["project"].get("target_language", DEFAULT_TARGET_LANGUAGE),
        panel_gutter_px=comic.get("panel_gutter_px", DEFAULT_PANEL_GUTTER_PX),
    )


def load_preferences(path: str | Path) -> dict[str, Any]:
    return read_json(path)


def validate_preferences(preferences: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(preferences, dict):
        return ["preferences must be an object"]

    project_config = preferences.get("project")
    if not isinstance(project_config, dict):
        errors.append("project must be an object")
    else:
        mode = project_config.get("mode")
        if not isinstance(mode, str) or mode not in PROJECT_MODES:
            errors.append("project.mode must be private_experiment, licensed_commercial, or public_domain")

        target_format = project_config.get("target_format")
        if not isinstance(target_format, str) or target_format not in TARGET_FORMATS:
            errors.append("project.target_format must be manga_page, color_comic, webtoon, or storyboard_only")

        automation_level = project_config.get("automation_level")
        if type(automation_level) is not int or automation_level not in AUTOMATION_LEVELS:
            errors.append("project.automation_level must be 1, 2, or 3")

        human_review = project_config.get("human_review")
        if not isinstance(human_review, bool):
            errors.append("project.human_review must be a boolean")

        if "target_language" in project_config:
            language = project_config["target_language"]
            if not isinstance(language, str) or not language.strip():
                errors.append("project.target_language must be a non-empty string")

    input_config = preferences.get("input")
    if not isinstance(input_config, dict):
        errors.append("input must be an object")
    else:
        formats = input_config.get("supported_formats")
        if formats != SUPPORTED_FORMATS:
            errors.append("input.supported_formats must be ['txt', 'epub']")

    comic_config = preferences.get("comic")
    if not isinstance(comic_config, dict):
        errors.append("comic must be an object")
    else:
        trim_size = comic_config.get("trim_size")
        if not isinstance(trim_size, str) or trim_size not in TRIM_SIZES:
            errors.append("comic.trim_size must be B5, A4, or manga-standard")

        target_pages = comic_config.get("target_pages")
        if type(target_pages) is not int or target_pages < 1:
            errors.append("comic.target_pages must be a positive integer")

        page_count_policy = comic_config.get("page_count_policy")
        if not isinstance(page_count_policy, str) or page_count_policy not in PAGE_COUNT_POLICIES:
            errors.append("comic.page_count_policy must be story_first_variable, fixed_budget, or soft_target")

        page_size_px = comic_config.get("page_size_px")
        if not isinstance(page_size_px, dict):
            errors.append("comic.page_size_px must be an object")
        else:
            width = page_size_px.get("width")
            height = page_size_px.get("height")
            if type(width) is not int or type(height) is not int or min(width, height) < DEFAULT_MINIMUM_SHORT_EDGE_PX:
                errors.append(f"comic.page_size_px width and height must be integers >= {DEFAULT_MINIMUM_SHORT_EDGE_PX}")
            elif height <= width:
                errors.append("comic.page_size_px must be portrait orientation")

        minimum_short_edge = comic_config.get("minimum_short_edge_px")
        if type(minimum_short_edge) is not int or minimum_short_edge < DEFAULT_MINIMUM_SHORT_EDGE_PX:
            errors.append(f"comic.minimum_short_edge_px must be an integer >= {DEFAULT_MINIMUM_SHORT_EDGE_PX}")
        elif isinstance(page_size_px, dict) and all(type(page_size_px.get(key)) is int for key in ("width", "height")):
            if min(page_size_px["width"], page_size_px["height"]) < minimum_short_edge:
                errors.append("comic.minimum_short_edge_px must not exceed the configured page's short edge")

        if "panel_gutter_px" in comic_config:
            gutter = comic_config["panel_gutter_px"]
            if type(gutter) is not int or gutter < 0:
                errors.append("comic.panel_gutter_px must be a non-negative integer")

        compression_mode = comic_config.get("compression_mode")
        if not isinstance(compression_mode, str) or compression_mode not in COMPRESSION_MODES:
            errors.append("comic.compression_mode must be essence, standard, or complete")

    approvals = preferences.get("approvals")
    if not isinstance(approvals, dict):
        errors.append("approvals must be an object")
    else:
        mode = approvals.get("after_first_chapter")
        if not isinstance(mode, str) or mode not in APPROVAL_MODES:
            errors.append("approvals.after_first_chapter must be chapter, every_n_chapters, or auto_after_first")

    visuals = preferences.get("visuals")
    if not isinstance(visuals, dict):
        errors.append("visuals must be an object")
    else:
        if not isinstance(visuals.get("style_family"), str) or not visuals["style_family"].strip():
            errors.append("visuals.style_family must be a non-empty string")

    image_generation = preferences.get("image_generation")
    if not isinstance(image_generation, dict):
        errors.append("image_generation must be an object")
    else:
        finished_page_text = image_generation.get("finished_page_text")
        if not isinstance(finished_page_text, str) or finished_page_text not in FINISHED_PAGE_TEXT_MODES:
            errors.append("image_generation.finished_page_text must be image2_embedded or deterministic_lettering_fallback")

        if image_generation.get("forbid_text_in_finished_pages") is not False:
            errors.append("image_generation.forbid_text_in_finished_pages must be false for finished-page image2 workflow")

        if not isinstance(image_generation.get("fallback_page_art_forbids_text"), bool):
            errors.append("image_generation.fallback_page_art_forbids_text must be a boolean")

    return errors
