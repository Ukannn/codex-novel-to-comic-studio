"""Chapter QC's report, severity, and workflow boundary contracts."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "TOOLS"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from novel_to_comic.qc import qc_chapter


class QualityControlContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "ch01"
        self.root.mkdir()
        self.storyboard = self.root / "storyboard.json"
        self.storyboard.write_text(json.dumps({"pages": [{
            "page": 1,
            "panels": [{"panel": 1, "dialogue": [{"text": "Hello"}]}],
        }]}), encoding="utf-8")
        self.report = self.root / "qc-report.json"

    def image(self, directory, size=(20, 30), color="red"):
        target = self.root / directory / "page-001.png"
        target.parent.mkdir()
        with Image.new("RGB", size, color) as image:
            image.save(target)
        return target

    def check(self):
        return qc_chapter(
            self.storyboard, self.root / "page-art", self.root / "finished-pages", self.report,
            expected_size=(20, 30),
        )

    def test_valid_fallback_chapter_report_round_trips(self):
        self.image("page-art")
        self.image("finished-pages")
        report = self.check()
        self.assertEqual(report, {
            "chapter": "ch01", "page_count": 1,
            "expected_size": {"width": 20, "height": 30},
            "issues": [], "blocking_open_issues": 0, "status": "pass",
        })
        self.assertEqual(json.loads(self.report.read_text(encoding="utf-8")), report)

    def test_finished_page_workflow_does_not_require_fallback_art(self):
        self.image("finished-pages")
        report = qc_chapter(
            self.storyboard, None, self.root / "finished-pages", self.report,
            expected_size=(20, 30),
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issues"], [])

    def test_cli_accepts_finished_pages_without_fallback_art(self):
        self.image("finished-pages")
        result = subprocess.run([
            sys.executable, str(TOOLS / "qc_chapter.py"), str(self.storyboard),
            "--finished-pages", str(self.root / "finished-pages"),
            "--out", str(self.report), "--width", "20", "--height", "30",
        ], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_corrupt_image_is_a_blocking_issue_without_losing_the_report(self):
        self.image("page-art")
        finished = self.image("finished-pages")
        finished.write_bytes(b"not an image")
        report = self.check()
        self.assertEqual(report["status"], "needs_fix")
        self.assertEqual(report["blocking_open_issues"], 1)
        self.assertEqual(report["issues"][0]["issue_id"], "page-001-finished_page-unreadable")
        self.assertEqual(json.loads(self.report.read_text(encoding="utf-8")), report)

    def test_qc_still_checks_other_pages_after_a_corrupt_image(self):
        self.image("page-art")
        finished = self.image("finished-pages")
        finished.write_bytes(b"not an image")
        data = json.loads(self.storyboard.read_text(encoding="utf-8"))
        data["pages"].append({"page": 2, "panels": [{"dialogue": [{"text": "Next"}]}]})
        self.storyboard.write_text(json.dumps(data), encoding="utf-8")
        report = self.check()
        self.assertEqual(report["blocking_open_issues"], 3)
        self.assertEqual([issue["issue_id"] for issue in report["issues"]], [
            "page-001-finished_page-unreadable",
            "page-002-page_art-missing", "page-002-finished_page-missing",
        ])

    def test_missing_requested_images_are_blocking(self):
        report = self.check()
        self.assertEqual(report["status"], "needs_fix")
        self.assertEqual(report["blocking_open_issues"], 2)
        self.assertEqual([issue["issue_id"] for issue in report["issues"]], [
            "page-001-page_art-missing", "page-001-finished_page-missing",
        ])

    def test_wrong_size_is_high_severity(self):
        self.image("page-art", size=(20, 29))
        self.image("finished-pages", size=(19, 30))
        report = self.check()
        self.assertEqual(report["blocking_open_issues"], 2)
        self.assertEqual([issue["severity"] for issue in report["issues"]], ["high", "high"])

    def test_silent_page_and_sparse_art_are_nonblocking_observations(self):
        self.storyboard.write_text(json.dumps({"pages": [{"page": 1, "panels": []}]}), encoding="utf-8")
        self.image("page-art", color="white")
        self.image("finished-pages")
        report = self.check()
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["blocking_open_issues"], 0)
        self.assertEqual([issue["issue_id"] for issue in report["issues"]], [
            "page-001-page_art-large-margin", "page-001-no-reader-text",
        ])


if __name__ == "__main__":
    unittest.main()
