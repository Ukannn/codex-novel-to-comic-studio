"""Observable rendering/export contracts, using tiny synthetic page fixtures."""

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "TOOLS"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from novel_to_comic.bind import bind_pages
from novel_to_comic.compose import compose_chapter_pages
from novel_to_comic.lettering import letter_chapter_pages, normalize_directory, normalize_page_image
from novel_to_comic.layout import panel_boxes


class RenderingContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def storyboard(self, layout, panel_count):
        path = self.root / "storyboard.json"
        path.write_text(json.dumps({"pages": [{
            "page": 1,
            "layout": layout,
            "panels": [{"panel": index} for index in range(1, panel_count + 1)],
        }]}), encoding="utf-8")
        return path

    def image(self, path, size, color):
        path.parent.mkdir(parents=True, exist_ok=True)
        with Image.new("RGB", size, color) as image:
            image.save(path)

    def test_compose_preserves_panel_positions_and_full_canvas_gutters(self):
        colors = ["red", "blue", "green", "yellow"]
        for index, color in enumerate(colors, start=1):
            self.image(self.root / "panels" / f"p001-{index:02d}.png", (18, 28), color)
        outputs = compose_chapter_pages(
            self.storyboard("2x2", 4), self.root / "panels", self.root / "pages",
            page_size=(40, 60), gutter=4,
        )
        self.assertEqual(outputs, [self.root / "pages" / "page-001.png"])
        with Image.open(outputs[0]) as page:
            self.assertEqual(page.size, (40, 60))
            self.assertEqual(page.getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(page.getpixel((39, 0)), (0, 0, 255))
            self.assertEqual(page.getpixel((0, 59)), (0, 128, 0))
            self.assertEqual(page.getpixel((39, 59)), (255, 255, 0))
            self.assertEqual(page.getpixel((19, 20)), (255, 255, 255))
            self.assertEqual(page.getpixel((10, 30)), (255, 255, 255))

    def test_compose_splash_uses_whole_canvas(self):
        self.image(self.root / "panels" / "p001-01.png", (40, 60), "red")
        outputs = compose_chapter_pages(
            self.storyboard("splash", 1), self.root / "panels", self.root / "pages",
            page_size=(40, 60),
        )
        with Image.open(outputs[0]) as page:
            self.assertEqual(page.getextrema(), ((255, 255), (0, 0), (0, 0)))

    def test_three_by_two_layout_keeps_row_major_reading_order(self):
        self.assertEqual(panel_boxes("3x2", (40, 80), 4, 6), [
            (0, 0, 18, 24), (22, 0, 40, 24),
            (0, 28, 18, 52), (22, 28, 40, 52),
            (0, 56, 18, 80), (22, 56, 40, 80),
        ])

    def test_story_led_layout_uses_enough_rows_for_odd_panel_count(self):
        self.assertEqual(panel_boxes("story-led", (40, 60), 4, 3), [
            (0, 0, 18, 28), (22, 0, 40, 28), (0, 32, 18, 60),
        ])

    def test_compose_keeps_missing_panel_placeholder(self):
        outputs = compose_chapter_pages(
            self.storyboard("splash", 1), self.root / "missing-panels", self.root / "pages",
            page_size=(100, 100),
        )
        with Image.open(outputs[0]) as page:
            self.assertEqual(page.getpixel((0, 0)), (180, 180, 180))
            self.assertEqual(page.getpixel((50, 80)), (245, 245, 245))

    def test_lettering_retains_its_own_safe_margin_and_gutter(self):
        self.image(self.root / "art" / "page-001.png", (1000, 1400), "white")
        captured = []
        with patch("novel_to_comic.lettering._draw_panel_lettering", side_effect=lambda draw, panel, box, *fonts: captured.append(box)):
            outputs = letter_chapter_pages(
                self.storyboard("2x2", 4), self.root / "art", self.root / "finished",
                page_size=(1000, 1400),
            )
        self.assertEqual(captured, [
            (82, 82, 483, 683), (517, 82, 918, 683),
            (82, 717, 483, 1318), (517, 717, 918, 1318),
        ])
        self.assertEqual(outputs, [self.root / "finished" / "page-001.png"])

    def test_lettering_splash_retains_safe_margin(self):
        self.image(self.root / "art" / "page-001.png", (1000, 1400), "white")
        with patch("novel_to_comic.lettering._draw_panel_lettering") as draw:
            letter_chapter_pages(
                self.storyboard("splash", 1), self.root / "art", self.root / "finished",
                page_size=(1000, 1400),
            )
        self.assertEqual(draw.call_args.args[2], (82, 82, 918, 1318))

    def test_normalization_contains_and_centers_art_without_cropping(self):
        source, target = self.root / "input.png", self.root / "out" / "page-001.png"
        self.image(source, (40, 20), "red")
        self.assertEqual(normalize_page_image(source, target, page_size=(80, 100)), target)
        with Image.open(target) as page:
            self.assertEqual(page.mode, "RGB")
            self.assertEqual(page.size, (80, 100))
            self.assertEqual(page.getpixel((0, 29)), (255, 255, 255))
            self.assertEqual(page.getpixel((0, 30)), (255, 0, 0))
            self.assertEqual(page.getpixel((79, 69)), (255, 0, 0))
            self.assertEqual(page.getpixel((0, 70)), (255, 255, 255))

    def test_normalize_directory_keeps_names_and_ignores_non_images(self):
        path = self.root / "page-001.png"
        self.image(path, (40, 20), "red")
        (self.root / "notes.txt").write_text("unchanged", encoding="utf-8")
        self.assertEqual(normalize_directory(self.root, page_size=(80, 100)), [path])
        with Image.open(path) as page:
            self.assertEqual(page.size, (80, 100))
        self.assertEqual((self.root / "notes.txt").read_text(encoding="utf-8"), "unchanged")

    def test_binding_preserves_lexicographic_order_and_result_shape(self):
        first = self.root / "ch01" / "page-001.png"
        second = self.root / "ch02" / "page-001.png"
        self.image(first, (20, 30), "red")
        self.image(second, (20, 30), "blue")
        result = bind_pages([second.parent, first.parent], self.root / "output", "test-book")
        self.assertEqual(result, {
            "pdf": str(self.root / "output" / "test-book.pdf"),
            "cbz": str(self.root / "output" / "test-book.cbz"),
            "page_count": "2",
        })
        pdf = Path(result["pdf"]).read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        with zipfile.ZipFile(result["cbz"]) as archive:
            self.assertEqual(archive.namelist(), ["page-001.png", "page-002.png"])
            self.assertEqual(archive.read("page-001.png"), first.read_bytes())
            self.assertEqual(archive.read("page-002.png"), second.read_bytes())

    def test_binding_empty_input_does_not_create_output(self):
        with self.assertRaisesRegex(ValueError, "No page images found to bind"):
            bind_pages([self.root], self.root / "output", "empty")
        self.assertFalse((self.root / "output").exists())

    def test_binding_releases_loaded_pages_if_a_later_page_cannot_decode(self):
        self.image(self.root / "pages" / "page-001.png", (20, 30), "red")
        (self.root / "pages" / "page-002.png").write_bytes(b"not an image")
        converted = []
        original_convert = Image.Image.convert

        def record_conversion(image, *args, **kwargs):
            result = original_convert(image, *args, **kwargs)
            converted.append(result)
            return result

        with patch.object(Image.Image, "convert", record_conversion):
            with self.assertRaises(OSError):
                bind_pages([self.root / "pages"], self.root / "output", "broken")
        self.assertTrue(converted)
        for image in converted:
            with self.assertRaises(ValueError):
                image.getpixel((0, 0))

    def test_binding_releases_loaded_pages_if_pdf_writing_fails(self):
        self.image(self.root / "pages" / "page-001.png", (20, 30), "red")
        converted = []
        original_convert = Image.Image.convert

        def record_conversion(image, *args, **kwargs):
            result = original_convert(image, *args, **kwargs)
            converted.append(result)
            return result

        with patch.object(Image.Image, "convert", record_conversion):
            with patch.object(Image.Image, "save", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    bind_pages([self.root / "pages"], self.root / "output", "broken")
        self.assertTrue(converted)
        for image in converted:
            with self.assertRaises(ValueError):
                image.getpixel((0, 0))


if __name__ == "__main__":
    unittest.main()
