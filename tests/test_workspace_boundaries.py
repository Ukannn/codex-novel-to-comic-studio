from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceBoundaries(unittest.TestCase):
    def test_generated_production_artifacts_stay_out_of_git_by_default(self):
        generated = [
            "source/my-book.txt", "source/manifest.json", "source/chapters/ch001.txt",
            "story-bible/narrative-map.json", "story-bible/characters.json",
            "comic-plan.json", "comic-plan.md", "chapters/ch01/page-script.json",
            "chapters/ch01/finished-pages/page-001.png", "visual-bible/style.md",
            "visual-bible/characters/char-001/reference-card.png", "output/book.pdf",
            "output/book.cbz", "logs/production.log",
        ]
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin"],
            cwd=ROOT, input="\n".join(generated) + "\n", capture_output=True, text=True,
            check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.splitlines()), set(generated))

    def test_tools_templates_and_original_demo_remain_trackable(self):
        tracked = [
            "TOOLS/novel_to_comic/source.py", "config/user-preferences.json",
            "rights/PROJECT_RIGHTS.md", "source/.gitkeep", "chapters/.gitkeep",
            "docs/architecture.md", "docs/assets/demo-page-001.png",
        ]
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin"],
            cwd=ROOT, input="\n".join(tracked) + "\n", capture_output=True, text=True,
            check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
