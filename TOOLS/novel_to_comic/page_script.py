"""Validation helpers for manga page scripts and dialogue coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .validation import has_text, page_report, read_document, validate_page_list


REQUIRED_SCRIPT_FIELDS = [
    "chapter",
    "status",
    "source_page_story_plan",
    "page_count_policy",
    "actual_page_count",
    "script_strategy",
    "critical_information",
    "pages",
]

REQUIRED_PAGE_FIELDS = [
    "page",
    "source_span",
    "story_job",
    "required_information",
    "reader_state",
    "information_density_goal",
    "non_omittable_causality",
    "source_lines",
    "panels",
]

READER_STATE_FIELDS = ["known_before", "new_information", "open_question"]
TEXT_FIELDS = ["dialogue", "captions", "sfx"]


def check_page_script(path: str | Path) -> dict[str, Any]:
    script_path = Path(path)
    script, issues = read_document(script_path, "page script")
    if issues:
        return _result(script_path, {}, issues)
    return validate_page_script(script, path=script_path)


def validate_page_script(script: object, *, path: str | Path = "<memory>") -> dict[str, Any]:
    """Validate an in-memory script without reading files or mutating the input."""
    script_path = Path(path)
    issues: list[dict[str, str]] = []
    if not isinstance(script, dict):
        issues.append({"file": str(script_path), "issue": "page script must be a JSON object"})
        return _result(script_path, {}, issues)

    for field in REQUIRED_SCRIPT_FIELDS:
        if field not in script:
            issues.append({"file": str(script_path), "issue": f"missing script field: {field}"})

    if script.get("page_count_policy") != "story_first_variable":
        issues.append({"file": str(script_path), "issue": "page_count_policy must be story_first_variable"})

    strategy = script.get("script_strategy")
    if not has_text(strategy):
        issues.append({"file": str(script_path), "issue": "script_strategy must explain the writing strategy"})
    elif "clarity" not in strategy.lower():
        issues.append({"file": str(script_path), "issue": "script_strategy must prioritize clarity over word count"})

    pages, page_issues = validate_page_list(script, script_path)
    issues.extend(page_issues)

    critical_ids = _critical_ids(script, script_path, issues)
    covered_ids = _check_pages(script_path, pages, issues)
    for critical_id in sorted(critical_ids - covered_ids):
        issues.append({"file": str(script_path), "issue": f"critical information not covered: {critical_id}"})

    return _result(script_path, script, issues)


def _critical_ids(script: dict[str, Any], path: Path, issues: list[dict[str, str]]) -> set[str]:
    critical_information = script.get("critical_information")
    if not isinstance(critical_information, list) or not critical_information:
        issues.append({"file": str(path), "issue": "critical_information must be a non-empty list"})
        return set()

    ids: set[str] = set()
    for index, item in enumerate(critical_information, start=1):
        if not isinstance(item, dict):
            issues.append({"file": str(path), "issue": f"critical_information {index} must be an object"})
            continue
        info_id = item.get("id")
        if not has_text(info_id):
            issues.append({"file": str(path), "issue": f"critical_information {index} missing id"})
            continue
        ids.add(info_id)
        for field in ("description", "source_span"):
            if not has_text(item.get(field)):
                issues.append({"file": str(path), "issue": f"critical_information {info_id} missing {field}"})
    return ids


def _check_pages(path: Path, pages: list[Any], issues: list[dict[str, str]]) -> set[str]:
    covered_ids: set[str] = set()
    seen_numbers: set[int] = set()
    for index, page in enumerate(pages, start=1):
        page_label = f"page {index}"
        if not isinstance(page, dict):
            issues.append({"file": str(path), "issue": f"{page_label} must be an object"})
            continue

        for field in REQUIRED_PAGE_FIELDS:
            if field not in page:
                issues.append({"file": str(path), "issue": f"{page_label} missing {field}"})

        page_number = page.get("page")
        if type(page_number) is not int:
            issues.append({"file": str(path), "issue": f"{page_label} missing numeric page"})
        else:
            if page_number in seen_numbers:
                issues.append({"file": str(path), "issue": f"duplicate page number: {page_number}"})
            seen_numbers.add(page_number)
            if page_number != index:
                issues.append({"file": str(path), "issue": f"page numbers must be sequential; expected {index}, got {page_number}"})

        for field in ("source_span", "story_job", "information_density_goal"):
            if not has_text(page.get(field)):
                issues.append({"file": str(path), "issue": f"{page_label} missing {field}"})

        required_information = page.get("required_information")
        if not isinstance(required_information, list) or not required_information:
            issues.append({"file": str(path), "issue": f"{page_label} missing required_information"})
        else:
            covered_ids.update(item for item in required_information if isinstance(item, str) and item.strip())

        reader_state = page.get("reader_state")
        if not isinstance(reader_state, dict):
            issues.append({"file": str(path), "issue": f"{page_label} reader_state must be an object"})
        else:
            for field in READER_STATE_FIELDS:
                if not has_text(reader_state.get(field)):
                    issues.append({"file": str(path), "issue": f"{page_label} reader_state missing {field}"})

        causality = page.get("non_omittable_causality")
        if not isinstance(causality, list) or not causality or not all(has_text(item) for item in causality):
            issues.append({"file": str(path), "issue": f"{page_label} missing non_omittable_causality"})

        source_lines = page.get("source_lines")
        if not isinstance(source_lines, dict):
            issues.append({"file": str(path), "issue": f"{page_label} source_lines must be an object"})
        else:
            kept = source_lines.get("kept")
            adapted = source_lines.get("adapted")
            if not isinstance(kept, list):
                issues.append({"file": str(path), "issue": f"{page_label} source_lines.kept must be a list"})
            if not isinstance(adapted, list) or not adapted:
                issues.append({"file": str(path), "issue": f"{page_label} source_lines.adapted must be a non-empty list"})

        _check_panels(path, page_label, page.get("panels"), issues)
    return covered_ids


def _check_panels(path: Path, page_label: str, panels: Any, issues: list[dict[str, str]]) -> None:
    if not isinstance(panels, list) or not panels:
        issues.append({"file": str(path), "issue": f"{page_label} panels must be a non-empty list"})
        return

    page_has_reader_text = False
    for panel_index, panel in enumerate(panels, start=1):
        if not isinstance(panel, dict):
            issues.append({"file": str(path), "issue": f"{page_label} panel {panel_index} must be an object"})
            continue
        for field in ("panel", "story_function", "visual_brief"):
            if field == "panel":
                if type(panel.get(field)) is not int:
                    issues.append({"file": str(path), "issue": f"{page_label} panel {panel_index} missing numeric panel"})
            elif not has_text(panel.get(field)):
                issues.append({"file": str(path), "issue": f"{page_label} panel {panel_index} missing {field}"})
        for text_field in TEXT_FIELDS:
            value = panel.get(text_field)
            if not isinstance(value, list):
                issues.append({"file": str(path), "issue": f"{page_label} panel {panel_index} {text_field} must be a list"})
                continue
            for item_index, item in enumerate(value, start=1):
                if not isinstance(item, dict) or not has_text(item.get("text")) or not has_text(item.get("purpose")):
                    issues.append({"file": str(path), "issue": f"{page_label} panel {panel_index} {text_field} item {item_index} needs text and purpose"})
                else:
                    page_has_reader_text = True
    if not page_has_reader_text:
        issues.append({"file": str(path), "issue": f"{page_label} has no reader-facing text"})


def _result(path: Path, script: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
    critical_information = script.get("critical_information") if isinstance(script.get("critical_information"), list) else []
    return page_report(path, script, issues, critical_information_count=len(critical_information))
