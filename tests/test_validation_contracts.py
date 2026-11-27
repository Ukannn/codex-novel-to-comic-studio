"""Behavior contracts for file validators and their command-line interfaces."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_core_tools import valid_page_script, valid_page_story_plan


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "TOOLS"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_director_briefs import check_briefs
from check_page_script import check_page_script
from check_page_story_plan import check_page_story_plan


VALID_BRIEF = """# Page purpose
Source trace: ch001:p1
Reference lock: No character reference required
Page layout: wide establishing panel above a close-up
Panel directives: rain strikes an empty street
Text directives: caption reads "After the rain."
Image2 prompt: draw the complete finished page
QC checklist: preserve the source beat
Output: chapters/ch01/finished-pages/page-001.png
"""


class PageValidationContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_document(self, name, document):
        path = self.root / name
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path

    def test_valid_reports_keep_existing_keys_and_counts(self):
        for name, document, checker, extra in (
            ("plan.json", valid_page_story_plan(), check_page_story_plan, {}),
            ("script.json", valid_page_script(), check_page_script, {"critical_information_count": 2}),
        ):
            with self.subTest(name=name):
                path = self.write_document(name, document)
                self.assertEqual(checker(path), {
                    "path": str(path), "status": "pass", "actual_page_count": 2,
                    "declared_page_count": 2, "issues": [], **extra,
                })

    def test_missing_invalid_json_and_non_object_reports(self):
        for name, checker, kind in (
            ("plan.json", check_page_story_plan, "page story plan"),
            ("script.json", check_page_script, "page script"),
        ):
            path = self.root / name
            for contents, expected in (
                (None, f"{kind} not found"),
                ("{", "invalid JSON: Expecting property name enclosed in double quotes"),
                ("[]", f"{kind} must be a JSON object"),
            ):
                with self.subTest(name=name, contents=contents):
                    if contents is not None:
                        path.write_text(contents, encoding="utf-8")
                    report = checker(path)
                    self.assertEqual(report["status"], "needs_fix")
                    self.assertEqual(report["actual_page_count"], 0)
                    self.assertEqual(report["declared_page_count"], None)
                    self.assertEqual(report["issues"], [{"file": str(path), "issue": expected}])

    def test_story_plan_preserves_page_order_diagnostics(self):
        plan = valid_page_story_plan()
        plan["pages"][1]["page"] = 1
        plan["pages"][1]["story_job"] = "tell the story"
        path = self.write_document("plan.json", plan)
        self.assertEqual(check_page_story_plan(path)["issues"], [
            {"file": str(path), "issue": "duplicate page number: 1"},
            {"file": str(path), "issue": "page numbers must be sequential; expected 2, got 1"},
            {"file": str(path), "issue": "page 2 story_job is too vague for manga adaptation"},
        ])

    def test_script_preserves_reader_text_and_coverage_diagnostics(self):
        script = valid_page_script()
        script["pages"][1]["required_information"] = ["hero_problem"]
        script["pages"][1]["panels"][0]["captions"] = []
        script["pages"][1]["panels"][0]["sfx"] = []
        path = self.write_document("script.json", script)
        self.assertEqual(check_page_script(path)["issues"], [
            {"file": str(path), "issue": "page 2 has no reader-facing text"},
            {"file": str(path), "issue": "critical information not covered: chapter_hook"},
        ])

    def test_wrong_nested_shapes_produce_reports(self):
        for name, factory, checker in (
            ("plan.json", valid_page_story_plan, check_page_story_plan),
            ("script.json", valid_page_script, check_page_script),
        ):
            for value in (None, "not pages", {"page": 1}, [None], [{}]):
                with self.subTest(name=name, value=value):
                    document = factory()
                    document["pages"] = copy.deepcopy(value)
                    path = self.write_document(name, document)
                    report = checker(path)
                    self.assertEqual(report["status"], "needs_fix")
                    self.assertTrue(report["issues"])

    def test_page_cli_exit_status_and_report_are_stable(self):
        for name, factory, checker in (
            ("check_page_story_plan.py", valid_page_story_plan, check_page_story_plan),
            ("check_page_script.py", valid_page_script, check_page_script),
        ):
            for document, expected_exit in ((factory(), 0), ({}, 1)):
                with self.subTest(name=name, expected_exit=expected_exit):
                    path = self.write_document("input.json", document)
                    completed = subprocess.run(
                        [sys.executable, str(TOOLS / name), str(path)],
                        cwd=self.root, capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(completed.returncode, expected_exit, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    self.assertEqual(json.loads(completed.stdout), checker(path))


class DirectorBriefContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_empty_directory_report(self):
        self.assertEqual(check_briefs(self.root), {
            "briefs": 0,
            "issues": [{"file": str(self.root), "issue": "no director brief files found"}],
            "status": "needs_fix",
        })

    def test_valid_brief_without_named_character(self):
        path = self.root / "page-001-director-brief.md"
        path.write_text(VALID_BRIEF, encoding="utf-8")
        self.assertEqual(check_briefs(self.root), {"briefs": 1, "issues": [], "status": "pass"})

    def test_issues_follow_filename_then_rule_order(self):
        first = self.root / "page-001-director-brief.md"
        second = self.root / "page-002-director-brief.md"
        second.write_text(VALID_BRIEF.replace("No character reference required", "unlocked") + "\nno text", encoding="utf-8")
        first.write_text(VALID_BRIEF.replace("Source trace", "Origin") + "\n2x2", encoding="utf-8")
        self.assertEqual(check_briefs(self.root), {
            "briefs": 2,
            "issues": [
                {"file": str(first), "issue": "missing marker: Source trace"},
                {"file": str(first), "issue": "mechanical grid token found; describe manga panel geometry instead"},
                {"file": str(second), "issue": "missing character reference lock or explicit no-character statement"},
                {"file": str(second), "issue": "finished-page brief must include exact readable text, not forbid all text"},
            ],
            "status": "needs_fix",
        })

    def test_director_cli_exit_status_and_report_are_stable(self):
        for content, expected_exit in ((VALID_BRIEF, 0), ("draft", 1)):
            with self.subTest(expected_exit=expected_exit):
                path = self.root / "page-001-director-brief.md"
                path.write_text(content, encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, str(TOOLS / "check_director_briefs.py"), str(self.root)],
                    cwd=self.root, capture_output=True, text=True, check=False,
                )
                self.assertEqual(completed.returncode, expected_exit, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertEqual(json.loads(completed.stdout), check_briefs(self.root))


if __name__ == "__main__":
    unittest.main()
