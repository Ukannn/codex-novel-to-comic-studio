#!/usr/bin/env python3
"""Run basic QC for finished pages, optionally including fallback page art."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_to_comic.qc import qc_chapter
from novel_to_comic.config import load_production_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a chapter QC report.")
    parser.add_argument("storyboard", help="Path to chapters/chNN/storyboard.json")
    parser.add_argument("--page-art", help="Also check this fallback page-art directory when supplied")
    parser.add_argument("--finished-pages", required=True, help="Finished pages directory")
    parser.add_argument("--out", required=True, help="QC report path")
    parser.add_argument("--preferences", help="Project user-preferences.json; explicit size flags take precedence")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args()
    try:
        settings = load_production_settings(args.preferences)
        page_size = settings.page_size_with_overrides(args.width, args.height)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))

    report = qc_chapter(
        Path(args.storyboard),
        Path(args.page_art) if args.page_art else None,
        Path(args.finished_pages),
        Path(args.out),
        expected_size=page_size,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
