#!/usr/bin/env python3
"""Optional fallback: compose separate panel images into draft page images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_to_comic.compose import compose_chapter_pages
from novel_to_comic.config import load_production_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional fallback: compose separate panel images into draft pages.")
    parser.add_argument("storyboard", help="Path to chapters/chNN/storyboard.json")
    parser.add_argument("--finals", required=True, help="Directory containing separate panel images")
    parser.add_argument("--out", required=True, help="Output pages directory")
    parser.add_argument("--preferences", help="Project user-preferences.json; explicit size/gutter flags take precedence")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--gutter", type=int)
    args = parser.parse_args()
    try:
        settings = load_production_settings(args.preferences)
        page_size = settings.page_size_with_overrides(args.width, args.height)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))

    pages = compose_chapter_pages(
        Path(args.storyboard),
        Path(args.finals),
        Path(args.out),
        page_size=page_size,
        gutter=args.gutter if args.gutter is not None else settings.panel_gutter_px,
    )
    print(json.dumps({"pages": len(pages), "out": args.out}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
