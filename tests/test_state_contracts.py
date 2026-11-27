import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TOOLS"))
from novel_to_comic.state import detect_state
from novel_to_comic.artifacts import read_json
from test_core_tools import valid_page_script, valid_page_story_plan


def make_chapter(root, name="ch01"):
    for relative in (
        "rights/PROJECT_RIGHTS.md", "source/novel.txt", "story-bible/narrative-map.json",
        "visual-bible/STYLE_APPROVED", "visual-bible/reference-cards/APPROVED", "comic-plan.json",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    chapter = root / "chapters" / name
    chapter.mkdir(parents=True)
    for filename, data in [("page-story-plan.json", valid_page_story_plan()), ("page-script.json", valid_page_script())]:
        (chapter / filename).write_text(json.dumps(data), encoding="utf-8")
    for marker in ["PAGE_STORY_PLAN_APPROVED", "PAGE_SCRIPT_APPROVED", "STORYBOARD_APPROVED", "APPROVED"]:
        (chapter / marker).touch()
    (chapter / "storyboard.json").write_text('{"pages": []}', encoding="utf-8")
    for page in [1, 2]:
        for path in [chapter / f"director-briefs/page-{page:03d}-director-brief.md", chapter / f"finished-pages/page-{page:03d}.png"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder", encoding="utf-8")
    (chapter / "qc-report.json").write_text("{}", encoding="utf-8")
    for path in chapter.rglob("*"):
        if path.is_file():
            os.utime(path, (1000, 1000))
    return chapter


class StateContracts(unittest.TestCase):
    def test_stale_dependency_precedence_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapter = make_chapter(root)
            self.assertEqual(detect_state(root)["next_phase"], "phase5_bind")
            script = chapter / "page-script.json"
            os.utime(script, (2000, 2000))
            self.assertEqual(detect_state(root)["next_phase"], "phase4b_storyboard")
            os.utime(chapter / "storyboard.json", (2000, 2000))
            state = detect_state(root)
            self.assertEqual(state["next_phase"], "phase4b_director_briefs")
            self.assertEqual(state["missing"], "chapters/ch01/director-briefs/page-001-director-brief.md (stale; regenerate from newer page script)")
            for brief in (chapter / "director-briefs").iterdir():
                os.utime(brief, (2000, 2000))
            state = detect_state(root)
            self.assertEqual(state["next_phase"], "phase4c_generate_finished_pages")
            self.assertEqual(state["missing"], "chapters/ch01/finished-pages/page-001.png (stale; regenerate from newer director brief)")

    def test_missing_earlier_chapter_blocks_later_complete_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            early = make_chapter(root, "ch01")
            make_chapter(root, "ch02")
            (early / "PAGE_SCRIPT_APPROVED").unlink()
            state = detect_state(root)
            self.assertEqual(state["next_phase"], "phase4aa_page_script_review")
            self.assertEqual(state["missing"], "chapters/ch01/PAGE_SCRIPT_APPROVED")

    def test_missing_finished_page_uses_script_page_list_not_storyboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapter = make_chapter(root)
            (chapter / "finished-pages/page-002.png").unlink()
            self.assertEqual(detect_state(root)["missing"], "chapters/ch01/finished-pages/page-002.png")

    def test_existence_only_later_gates_and_both_exports_remain_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_chapter(root)
            (root / "output").mkdir()
            (root / "output/book.pdf").touch()
            self.assertEqual(detect_state(root)["next_phase"], "phase5_bind")
            (root / "output/book.cbz").touch()
            state = detect_state(root)
            self.assertEqual(state["next_phase"], "complete")
            self.assertEqual(set(state), {"project_root", "completed", "next_phase", "missing"})

    def test_each_document_is_read_once_per_inspection_without_persistent_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapter = make_chapter(root)
            with patch("novel_to_comic.validation.read_json", wraps=read_json) as read:
                self.assertEqual(detect_state(root)["next_phase"], "phase5_bind")
            self.assertEqual([call.args[0] for call in read.call_args_list], [
                chapter / "page-story-plan.json", chapter / "page-script.json",
            ])
            (chapter / "page-script.json").write_text("{}", encoding="utf-8")
            self.assertEqual(detect_state(root)["next_phase"], "phase4aa_manga_script")

    def test_unreadable_script_returns_repair_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapter = make_chapter(root)
            path = chapter / "page-script.json"
            path.write_bytes(b"\xff")
            state = detect_state(root)
            self.assertEqual(state["next_phase"], "phase4aa_manga_script")
            self.assertIn("needs_fix", state["missing"])


if __name__ == "__main__":
    unittest.main()
