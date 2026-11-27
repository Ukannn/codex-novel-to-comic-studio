"""A fresh import becomes visible to recovery only after its artifacts exist."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "TOOLS"))
from novel_to_comic.source import Chapter, ParsedSource, write_parsed_source
from novel_to_comic.state import detect_state


class IngestPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "rights").mkdir()
        (self.root / "rights" / "PROJECT_RIGHTS.md").write_text("Synthetic test source", encoding="utf-8")
        self.output = self.root / "source"
        self.parsed = ParsedSource(
            title="Synthetic 小说",
            full_text="全书内容\nSecond paragraph.",
            chapters=[Chapter(1, "Chapter 1", "第一章正文"), Chapter(2, "Chapter 2", "Second chapter.")],
        )

    def assert_not_published(self):
        self.assertFalse((self.output / "novel.txt").exists())
        self.assertEqual(detect_state(self.root)["next_phase"], "phase0_ingest")

    def test_success_keeps_existing_bytes_paths_and_manifest_schema(self):
        write_parsed_source(self.parsed, self.output)
        self.assertEqual((self.output / "novel.txt").read_bytes(), self.parsed.full_text.encode("utf-8"))
        for chapter in self.parsed.chapters:
            expected = f"{chapter.title}\n\n{chapter.text.strip()}\n".encode("utf-8")
            self.assertEqual((self.output / "chapters" / f"ch{chapter.index:03d}.txt").read_bytes(), expected)
        manifest = {
            "title": "Synthetic 小说", "chapter_count": 2,
            "chapters": [
                {"index": 1, "title": "Chapter 1", "path": "chapters/ch001.txt", "characters": 5},
                {"index": 2, "title": "Chapter 2", "path": "chapters/ch002.txt", "characters": 15},
            ],
        }
        self.assertEqual((self.output / "manifest.json").read_bytes(), (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        self.assertEqual(detect_state(self.root)["next_phase"], "phase1_story_bible")

    def test_first_chapter_write_failure_does_not_complete_fresh_import(self):
        # A directory at the destination reproduces a real write failure without
        # coupling the test to the persistence implementation.
        (self.output / "chapters" / "ch001.txt").mkdir(parents=True)
        with self.assertRaises(OSError):
            write_parsed_source(self.parsed, self.output)
        self.assert_not_published()
        self.assertFalse((self.output / "manifest.json").exists())

    def test_manifest_write_failure_does_not_complete_fresh_import(self):
        (self.output / "manifest.json").mkdir(parents=True)
        with self.assertRaises(OSError):
            write_parsed_source(self.parsed, self.output)
        self.assert_not_published()

    def test_final_novel_publish_failure_does_not_complete_fresh_import(self):
        real_replace = os.replace

        def fail_novel(source, destination):
            if Path(destination).name == "novel.txt":
                raise OSError("novel publication failed")
            real_replace(source, destination)

        with patch("novel_to_comic.artifacts.os.replace", side_effect=fail_novel):
            with self.assertRaisesRegex(OSError, "novel publication failed"):
                write_parsed_source(self.parsed, self.output)
        self.assert_not_published()
        self.assertTrue((self.output / "manifest.json").is_file())
        self.assertTrue((self.output / "chapters" / "ch002.txt").is_file())
        self.assertEqual(list(self.output.glob(".*.tmp")), [])

    def test_chapter_failure_preserves_existing_novel_file(self):
        (self.output / "chapters" / "ch001.txt").mkdir(parents=True)
        novel = self.output / "novel.txt"
        novel.write_bytes(b"previous complete novel")
        with self.assertRaises(OSError):
            write_parsed_source(self.parsed, self.output)
        self.assertEqual(novel.read_bytes(), b"previous complete novel")

    def test_final_publish_failure_preserves_existing_novel_file(self):
        self.output.mkdir()
        novel = self.output / "novel.txt"
        novel.write_bytes(b"previous complete novel")
        real_replace = os.replace

        def fail_novel(source, destination):
            if Path(destination) == novel:
                raise OSError("novel publication failed")
            real_replace(source, destination)

        with patch("novel_to_comic.artifacts.os.replace", side_effect=fail_novel):
            with self.assertRaisesRegex(OSError, "novel publication failed"):
                write_parsed_source(self.parsed, self.output)
        self.assertEqual(novel.read_bytes(), b"previous complete novel")


if __name__ == "__main__":
    unittest.main()
