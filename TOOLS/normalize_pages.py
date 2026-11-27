#!/usr/bin/env python3
"""Normalize comic page images to the configured A4 production canvas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_to_comic.config import load_production_settings
from novel_to_comic.lettering import A4_PAGE_SIZE as A4_PAGE_SIZE
from novel_to_comic.lettering import normalize_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize page images to A4 portrait 2480x3508 by default.")
    parser.add_argument("page_dir", help="Directory containing page images")
    parser.add_argument("--preferences", help="Project user-preferences.json; explicit size flags take precedence")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args()
    try:
        settings = load_production_settings(args.preferences)
        page_size = settings.page_size_with_overrides(args.width, args.height)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))

    outputs = normalize_directory(Path(args.page_dir), page_size=page_size)
    print(json.dumps({"normalized": len(outputs), "page_dir": args.page_dir, "size": list(page_size)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
