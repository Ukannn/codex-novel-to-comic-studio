import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "TOOLS"))
from novel_to_comic.artifacts import read_json, write_json, write_text


class ArtifactPersistenceTests(unittest.TestCase):
    def test_raw_text_is_exact_and_failed_replace_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chapter.txt"
            original = "中文 / 한국어\nNo added trailing newline"
            write_text(path, original)
            self.assertEqual(path.read_bytes(), original.encode("utf-8"))
            with patch("novel_to_comic.artifacts.os.replace", side_effect=OSError("disk error")):
                with self.assertRaisesRegex(OSError, "disk error"):
                    write_text(path, "replacement text")
            self.assertEqual(path.read_bytes(), original.encode("utf-8"))
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_utf8_format_and_nested_parent_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "report.json"
            data = {"title": "寒武 / 테스트", "pages": [1, 2]}
            write_json(path, data)
            self.assertEqual(path.read_bytes(), (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            self.assertEqual(read_json(path), data)

    def test_serialization_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_bytes(b"old content")
            with self.assertRaises(TypeError):
                write_json(path, {"bad": object()})
            self.assertEqual(path.read_bytes(), b"old content")
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_failed_replace_preserves_previous_document_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_bytes(b'{"old": true}\n')
            with patch("novel_to_comic.artifacts.os.replace", side_effect=OSError("disk error")):
                with self.assertRaisesRegex(OSError, "disk error"):
                    write_json(path, {"new": True})
            self.assertEqual(read_json(path), {"old": True})
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_replace_occurs_only_after_complete_document_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            write_json(path, {"old": True})
            real_replace = os.replace

            def observe_replace(source, destination):
                self.assertEqual(read_json(destination), {"old": True})
                self.assertEqual(read_json(source), {"new": "正文"})
                real_replace(source, destination)

            with patch("novel_to_comic.artifacts.os.replace", side_effect=observe_replace):
                write_json(path, {"new": "正文"})
            self.assertEqual(read_json(path), {"new": "正文"})

    def test_failed_stream_creation_releases_descriptor_and_temporary_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_bytes(b'{"old": true}')
            descriptor = None

            def fail_open(fd, *args, **kwargs):
                nonlocal descriptor
                descriptor = fd
                raise OSError("stream allocation failure")

            with patch("novel_to_comic.artifacts.os.fdopen", side_effect=fail_open):
                with self.assertRaisesRegex(OSError, "stream allocation failure"):
                    write_json(path, {"new": True})
            with self.assertRaises(OSError):
                os.fstat(descriptor)
            self.assertEqual(read_json(path), {"old": True})
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_existing_permissions_and_symlink_destination_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            write_json(path, {})
            path.chmod(0o640)
            link = Path(tmp) / "report-link.json"
            link.symlink_to(path.name)
            write_json(link, {"new": True})
            self.assertTrue(link.is_symlink())
            self.assertEqual(read_json(path), {"new": True})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_read_errors_keep_their_exception_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            with self.assertRaises(FileNotFoundError):
                read_json(path)
            path.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                read_json(path)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                read_json(path)


if __name__ == "__main__":
    unittest.main()
