"""Filesystem state detection for recoverable comic projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .page_story_plan import check_page_story_plan
from .page_script import validate_page_script
from .validation import read_document


PHASES = (
    ("phase0_rights_gate", "rights/PROJECT_RIGHTS.md"),
    ("phase0_ingest", "source/novel.txt"),
    ("phase1_story_bible", "story-bible/narrative-map.json"),
    ("phase2a_style_preview", "visual-bible/STYLE_APPROVED"),
    ("phase2b_reference_cards", "visual-bible/reference-cards/APPROVED"),
    ("phase3_comic_plan", "comic-plan.json"),
)


def detect_state(root: str | Path) -> dict[str, Any]:
    project_root = Path(root)
    completed: list[str] = []

    for next_phase, required_path in PHASES:
        if not (project_root / required_path).exists():
            return {
                "project_root": str(project_root),
                "completed": completed,
                "next_phase": next_phase,
                "missing": required_path,
            }
        completed.append(next_phase)

    chapter_state = _detect_chapter_state(project_root)
    if chapter_state:
        return {
            "project_root": str(project_root),
            "completed": completed,
            **chapter_state,
        }

    return {
        "project_root": str(project_root),
        "completed": completed,
        "next_phase": "phase4_chapter_loop",
        "missing": "chapters/ch001/storyboard.json",
    }


def _detect_chapter_state(project_root: Path) -> dict[str, str] | None:
    chapters_dir = project_root / "chapters"
    if not chapters_dir.exists():
        return None

    chapter_dirs = sorted(path for path in chapters_dir.glob("ch*") if path.is_dir())
    for chapter_dir in chapter_dirs:
        chapter_name = chapter_dir.name
        page_story_plan = chapter_dir / "page-story-plan.json"
        if not page_story_plan.exists():
            return {"next_phase": "phase4a_manga_story_adaptation", "missing": f"chapters/{chapter_name}/page-story-plan.json"}
        plan_check = check_page_story_plan(page_story_plan)
        if plan_check["status"] != "pass":
            return {
                "next_phase": "phase4a_manga_story_adaptation",
                "missing": f"chapters/{chapter_name}/page-story-plan.json (needs_fix; run TOOLS/check_page_story_plan.py)",
            }
        if not (chapter_dir / "PAGE_STORY_PLAN_APPROVED").exists():
            return {"next_phase": "phase4a_page_story_plan_review", "missing": f"chapters/{chapter_name}/PAGE_STORY_PLAN_APPROVED"}
        page_script = chapter_dir / "page-script.json"
        if not page_script.exists():
            return {"next_phase": "phase4aa_manga_script", "missing": f"chapters/{chapter_name}/page-script.json"}
        script, read_issues = read_document(page_script, "page script")
        if read_issues or validate_page_script(script, path=page_script)["status"] != "pass":
            return {
                "next_phase": "phase4aa_manga_script",
                "missing": f"chapters/{chapter_name}/page-script.json (needs_fix; run TOOLS/check_page_script.py)",
            }
        if not (chapter_dir / "PAGE_SCRIPT_APPROVED").exists():
            return {"next_phase": "phase4aa_page_script_review", "missing": f"chapters/{chapter_name}/PAGE_SCRIPT_APPROVED"}
        # The validated document is the authority for all downstream page checks.
        # Do not re-read it between briefs and images during one state inspection.
        page_numbers = [page["page"] for page in script["pages"]]
        storyboard_path = chapter_dir / "storyboard.json"
        if not storyboard_path.exists() or page_script.stat().st_mtime > storyboard_path.stat().st_mtime:
            return {"next_phase": "phase4b_storyboard", "missing": f"chapters/{chapter_name}/storyboard.json"}
        if not (chapter_dir / "STORYBOARD_APPROVED").exists():
            return {"next_phase": "phase4b_storyboard_review", "missing": f"chapters/{chapter_name}/STORYBOARD_APPROVED"}
        missing_brief = _missing_director_brief(project_root, page_script, chapter_name, page_numbers)
        if missing_brief:
            return {"next_phase": "phase4b_director_briefs", "missing": missing_brief}
        missing_finished_pages = _missing_finished_pages(project_root, chapter_name, page_numbers)
        if missing_finished_pages:
            return {"next_phase": "phase4c_generate_finished_pages", "missing": missing_finished_pages}
        if not (chapter_dir / "qc-report.json").exists():
            return {"next_phase": "phase4f_qc", "missing": f"chapters/{chapter_name}/qc-report.json"}
        if not (chapter_dir / "APPROVED").exists():
            return {"next_phase": "phase4_review", "missing": f"chapters/{chapter_name}/APPROVED"}

    if chapter_dirs:
        if list((project_root / "output").glob("*.pdf")) and list((project_root / "output").glob("*.cbz")):
            return {"next_phase": "complete", "missing": ""}
        return {"next_phase": "phase5_bind", "missing": "output/*.pdf and output/*.cbz"}
    return None


def _missing_director_brief(project_root: Path, page_script_path: Path, chapter_name: str, page_numbers: list[int]) -> str:
    for page_number in page_numbers:
        target = f"chapters/{chapter_name}/director-briefs/page-{page_number:03d}-director-brief.md"
        target_path = project_root / target
        if not target_path.exists():
            return target
        if page_script_path.stat().st_mtime > target_path.stat().st_mtime:
            return f"{target} (stale; regenerate from newer page script)"
    return ""


def _missing_finished_pages(project_root: Path, chapter_name: str, page_numbers: list[int]) -> str:
    for page_number in page_numbers:
        target = f"chapters/{chapter_name}/finished-pages/page-{page_number:03d}.png"
        target_path = project_root / target
        if not target_path.exists():
            return target
        brief_path = project_root / f"chapters/{chapter_name}/director-briefs/page-{page_number:03d}-director-brief.md"
        if brief_path.exists() and brief_path.stat().st_mtime > target_path.stat().st_mtime:
            return f"{target} (stale; regenerate from newer director brief)"
    return ""
