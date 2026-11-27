from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TOOLS"))
from novel_to_comic.config import (
    DEFAULT_MINIMUM_SHORT_EDGE_PX, DEFAULT_PAGE_SIZE, DEFAULT_PANEL_GUTTER_PX,
    ProductionSettings, load_preferences, load_production_settings, validate_preferences,
)


class ProductionSettingsTests(unittest.TestCase):
    def test_legacy_defaults_and_project_choices_remain_distinct(self):
        standalone = load_production_settings()
        project = load_production_settings(ROOT / "config/user-preferences.json")
        self.assertEqual(standalone.page_size, DEFAULT_PAGE_SIZE)
        self.assertEqual(standalone.minimum_short_edge_px, DEFAULT_MINIMUM_SHORT_EDGE_PX)
        self.assertEqual(standalone.panel_gutter_px, DEFAULT_PANEL_GUTTER_PX)
        self.assertEqual(standalone.target_language, "zh-CN")
        self.assertEqual(project.target_language, "en")
        self.assertEqual(project.page_size, (2480, 3508))

    def test_explicit_settings_and_each_dimension_override(self):
        prefs = load_preferences(ROOT / "config/user-preferences.json")
        prefs["comic"].update(page_size_px={"width": 3000, "height": 4200}, minimum_short_edge_px=2500, panel_gutter_px=12)
        prefs["project"]["target_language"] = "ko"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preferences.json"
            path.write_text(json.dumps(prefs), encoding="utf-8")
            settings = load_production_settings(path)
        self.assertEqual(settings.page_size, (3000, 4200))
        self.assertEqual(settings.minimum_short_edge_px, 2500)
        self.assertEqual(settings.panel_gutter_px, 12)
        self.assertEqual(settings.target_language, "ko")
        self.assertEqual(settings.page_size_with_overrides(), (3000, 4200))
        self.assertEqual(settings.page_size_with_overrides(width=96), (96, 4200))
        self.assertEqual(settings.page_size_with_overrides(height=128), (3000, 128))
        self.assertEqual(settings.page_size_with_overrides(96, 128), (96, 128))

    def test_settings_are_immutable_and_bad_overrides_rejected(self):
        settings = ProductionSettings()
        with self.assertRaises(FrozenInstanceError):
            settings.target_language = "ko"
        for value in [0, -1, True, 1.5]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                settings.page_size_with_overrides(width=value)

    def test_invalid_preference_shapes_are_diagnostics(self):
        for value in [None, [], True, "bad", 42]:
            self.assertEqual(validate_preferences(value), ["preferences must be an object"])
        preferences = load_preferences(ROOT / "config/user-preferences.json")
        for section, key in [
            ("project", "mode"), ("project", "target_format"),
            ("project", "automation_level"), ("comic", "trim_size"),
            ("comic", "page_count_policy"), ("comic", "compression_mode"),
            ("approvals", "after_first_chapter"), ("image_generation", "finished_page_text"),
        ]:
            for value in [[], {}]:
                with self.subTest(section=section, key=key, value=value):
                    invalid = deepcopy(preferences)
                    invalid[section][key] = value
                    self.assertTrue(validate_preferences(invalid))

    def test_invalid_production_values_are_rejected_without_type_coercion(self):
        preferences = load_preferences(ROOT / "config/user-preferences.json")
        for section, key, value in [
            ("project", "automation_level", True), ("project", "target_language", ""),
            ("comic", "target_pages", True), ("comic", "panel_gutter_px", -1),
            ("comic", "panel_gutter_px", True), ("comic", "minimum_short_edge_px", 4000),
            ("comic", "page_size_px", {"width": True, "height": 3508}),
        ]:
            with self.subTest(section=section, key=key):
                invalid = deepcopy(preferences)
                invalid[section][key] = value
                self.assertTrue(validate_preferences(invalid))

    def test_invalid_file_does_not_silently_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preferences.json"
            with self.assertRaises(FileNotFoundError):
                load_production_settings(path)
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preferences must be an object"):
                load_production_settings(path)


if __name__ == "__main__":
    unittest.main()
