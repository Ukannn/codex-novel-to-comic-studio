#!/usr/bin/env python3
"""Add dialogue, captions, and SFX to page art for one chapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_to_comic.config import load_production_settings
from novel_to_comic.lettering import A4_PAGE_SIZE as A4_PAGE_SIZE
from novel_to_comic.lettering import letter_chapter_pages


def main() -> int:
    parser = argparse.ArgumentParser(description="Create finished readable comic pages from page art and storyboard text.")
    parser.add_argument("storyboard", help="Path to chapters/chNN/storyboard.json")
    parser.add_argument("--page-art", required=True, help="Directory containing page-art/page-001.png etc.")
    parser.add_argument("--out", required=True, help="Output finished-pages directory")
    parser.add_argument("--preferences", help="Project user-preferences.json; explicit size flags take precedence")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args()
    try:
        settings = load_production_settings(args.preferences)
        page_size = settings.page_size_with_overrides(args.width, args.height)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))

    pages = letter_chapter_pages(
        Path(args.storyboard),
        Path(args.page_art),
        Path(args.out),
        page_size=page_size,
    )
    print(json.dumps({"pages": len(pages), "out": args.out, "size": list(page_size)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
