"""Public executable and import contracts, independent of the working directory."""

import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "TOOLS"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

CLI_FLAGS = {
    "bind.py": ("--out", "--book-slug"),
    "check_director_briefs.py": (),
    "check_page_script.py": (),
    "check_page_story_plan.py": (),
    "check_state.py": (),
    "compose.py": ("--finals", "--out", "--width", "--height", "--gutter"),
    "letter_chapter.py": ("--page-art", "--out", "--width", "--height"),
    "make_image_tasks.py": ("--visual-bible", "--chapter", "--out"),
    "normalize_pages.py": ("--width", "--height"),
    "parse_source.py": ("--out",),
    "qc_chapter.py": ("--page-art", "--finished-pages", "--out", "--width", "--height"),
}


class CommandContractTests(unittest.TestCase):
    def test_all_existing_commands_offer_help_from_an_external_directory(self):
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as working_directory:
            for command, flags in CLI_FLAGS.items():
                with self.subTest(command=command):
                    result = subprocess.run(
                        [sys.executable, str(TOOLS / command), "--help"],
                        cwd=working_directory, env=environment,
                        capture_output=True, text=True, check=False, timeout=15,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertIn("usage:", result.stdout.lower())
                    for flag in flags:
                        self.assertIn(flag, result.stdout)
            self.assertEqual(list(Path(working_directory).iterdir()), [])

    def test_validator_imports_still_resolve_to_canonical_implementations(self):
        for command, module, name in (
            ("check_page_script", "page_script", "check_page_script"),
            ("check_page_story_plan", "page_story_plan", "check_page_story_plan"),
            ("check_director_briefs", "director_briefs", "check_briefs"),
        ):
            with self.subTest(command=command):
                adapter = importlib.import_module(command)
                service = importlib.import_module(f"novel_to_comic.{module}")
                self.assertIs(getattr(adapter, name), getattr(service, name))


if __name__ == "__main__":
    unittest.main()
