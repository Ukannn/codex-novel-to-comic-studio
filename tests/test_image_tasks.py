import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TOOLS"))
from novel_to_comic.image_tasks import build_image_tasks, write_image_tasks


def sample_storyboard():
    return {"pages": [{"page": 1, "layout": "opening splash", "panels": [{
        "panel": 1, "shot": "wide", "angle": "low", "description": "A door opens.",
        "chars": [{"id": "char-001", "outfit": "travel", "expression": "alert"}],
        "setting": "hall", "setting_time": "night",
        "dialogue": [{"speaker": "char-001", "text": "Who's there?"}],
        "captions": [{"text": "After midnight."}], "sfx": [{"text": "KNOCK"}],
    }]}]}


class ImageTaskContracts(unittest.TestCase):
    def test_default_task_and_exact_prompt_remain_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storyboard = root / "storyboard.json"
            storyboard.write_text(json.dumps(sample_storyboard()), encoding="utf-8")
            tasks = build_image_tasks(storyboard, root / "visual-bible", "ch01")
            self.assertEqual(len(tasks), 1)
            task = tasks[0]
            self.assertEqual(set(task), {"chapter", "page", "panel_count", "target", "target_size_px", "minimum_short_edge_px", "trim_size", "layout", "references", "prompt"})
            self.assertEqual(task["target"], "chapters/ch01/finished-pages/page-001.png")
            self.assertEqual(task["target_size_px"], {"width": 2480, "height": 3508})
            self.assertEqual(task["minimum_short_edge_px"], 2048)
            self.assertEqual(task["trim_size"], "A4")
            self.assertEqual(task["prompt"],
                "Generate one complete readable finished manga page in A4 portrait, final production target 2480x3508 px or higher, "
                "minimum short edge 2048 px. Use the layout intent: opening splash. "
                "Page content: Panel 1: wide shot, low angle. A door opens. Characters: char-001. "
                "Exact Chinese reader text to render cleanly in balloons, captions, and SFX: "
                "Panel 1 caption: After midnight. Panel 1 char-001: Who's there? Panel 1 SFX: KNOCK "
                "Use supplied references for identity, wardrobe, and setting consistency across all panels on the page. "
                "Keep all text inside safe areas, avoid covering faces, hands, weapons, and key action, and do not add extra random glyphs, signatures, subtitles, or watermarks.")
            self.assertEqual([ref["role"] for ref in task["references"]], [
                "char-001 canonical face", "char-001 outfit travel", "char-001 expression alert", "hall setting",
            ])
            output = root / "out" / "tasks.json"
            write_image_tasks(tasks, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), tasks)

    def test_approved_reference_card_replaces_legacy_references_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = sample_storyboard()
            data["pages"][0]["panels"] *= 2
            storyboard = root / "storyboard.json"
            storyboard.write_text(json.dumps(data), encoding="utf-8")
            visual = root / "visual-bible"
            card = visual / "characters/char-001/reference-card.png"
            card.parent.mkdir(parents=True)
            card.touch()
            references = build_image_tasks(storyboard, visual, "ch01")[0]["references"]
            self.assertEqual(len(references), 2)
            self.assertEqual(references[0], {"path": str(card), "role": "char-001 approved character reference card"})

    def test_cli_default_result_shape_and_output_from_external_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storyboard = root / "storyboard.json"
            storyboard.write_text(json.dumps(sample_storyboard()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "TOOLS/make_image_tasks.py"), str(storyboard), "--chapter", "ch01"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"tasks": 1, "out": "chapters/ch01/image-tasks.json"})
            self.assertTrue((root / "chapters/ch01/image-tasks.json").is_file())


if __name__ == "__main__":
    unittest.main()
