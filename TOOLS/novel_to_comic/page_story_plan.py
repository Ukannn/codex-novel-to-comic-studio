"""Validation helpers for reader-first manga page story plans."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .validation import has_text, page_report, read_document, validate_page_list


REQUIRED_PLAN_FIELDS = [
    "chapter",
    "status",
    "page_count_policy",
    "actual_page_count",
    "reader_promise",
    "must_include",
    "asset_gaps_before_director_briefs",
    "pages",
]

REQUIRED_PAGE_FIELDS = [
    "page",
    "source_span",
    "story_job",
    "reader_enters_with",
    "reader_leaves_with",
    "beats",
    "tone",
    "info_density",
    "handoff",
]


def check_page_story_plan(path: str | Path) -> dict[str, Any]:
    plan_path = Path(path)
    plan, issues = read_document(plan_path, "page story plan")
    if issues:
        return page_report(plan_path, {}, issues)
    return validate_page_story_plan(plan, path=plan_path)


def validate_page_story_plan(plan: object, *, path: str | Path = "<memory>") -> dict[str, Any]:
    """Validate an in-memory plan without reading files or mutating the input."""
    plan_path = Path(path)
    issues: list[dict[str, str]] = []
    if not isinstance(plan, dict):
        issues.append({"file": str(plan_path), "issue": "page story plan must be a JSON object"})
        return page_report(plan_path, {}, issues)

    for field in REQUIRED_PLAN_FIELDS:
        if field not in plan:
            issues.append({"file": str(plan_path), "issue": f"missing plan field: {field}"})

    if plan.get("page_count_policy") != "story_first_variable":
        issues.append({"file": str(plan_path), "issue": "page_count_policy must be story_first_variable"})

    pages, page_issues = validate_page_list(plan, plan_path)
    issues.extend(page_issues)

    if not isinstance(plan.get("must_include"), list) or not plan.get("must_include"):
        issues.append({"file": str(plan_path), "issue": "must_include must list source beats that cannot be dropped"})

    asset_gaps = plan.get("asset_gaps_before_director_briefs")
    if not isinstance(asset_gaps, list):
        issues.append({"file": str(plan_path), "issue": "asset_gaps_before_director_briefs must be a list"})
    else:
        for index, gap in enumerate(asset_gaps, start=1):
            if not isinstance(gap, dict):
                issues.append({"file": str(plan_path), "issue": f"asset gap {index} must be an object"})
                continue
            for field in ("id", "need", "risk"):
                if not has_text(gap.get(field)):
                    issues.append({"file": str(plan_path), "issue": f"asset gap {index} missing {field}"})

    _check_pages(plan_path, pages, issues)
    return page_report(plan_path, plan, issues)


def _check_pages(path: Path, pages: list[Any], issues: list[dict[str, str]]) -> None:
    seen_numbers: set[int] = set()
    for index, page in enumerate(pages, start=1):
        page_label = f"page {index}"
        if not isinstance(page, dict):
            issues.append({"file": str(path), "issue": f"{page_label} must be an object"})
            continue
        for field in REQUIRED_PAGE_FIELDS:
            value = page.get(field)
            if field == "beats":
                if not isinstance(value, list) or not value or not all(has_text(item) for item in value):
                    issues.append({"file": str(path), "issue": f"{page_label} missing useful beats"})
            elif field == "page":
                if type(value) is not int:
                    issues.append({"file": str(path), "issue": f"{page_label} missing numeric page"})
            elif not has_text(value):
                issues.append({"file": str(path), "issue": f"{page_label} missing {field}"})

        page_number = page.get("page")
        if type(page_number) is int:
            if page_number in seen_numbers:
                issues.append({"file": str(path), "issue": f"duplicate page number: {page_number}"})
            seen_numbers.add(page_number)
            if page_number != index:
                issues.append({"file": str(path), "issue": f"page numbers must be sequential; expected {index}, got {page_number}"})

        if _looks_like_vague_summary(page.get("story_job")):
            issues.append({"file": str(path), "issue": f"{page_label} story_job is too vague for manga adaptation"})


def _looks_like_vague_summary(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    vague_jobs = {
        "introduce everything quickly",
        "tell the story",
        "explain the chapter",
        "show what happens",
        "lore montage",
    }
    return normalized in vague_jobs
