#!/usr/bin/env python3
"""Create a half-manual image-generation task sheet from storyboard JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_to_comic.config import load_production_settings
from novel_to_comic.image_tasks import build_image_tasks, write_image_tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Build image-generation tasks for one chapter.")
    parser.add_argument("storyboard", help="Path to chapters/chNN/storyboard.json")
    parser.add_argument("--visual-bible", default="visual-bible", help="Path to visual bible directory")
    parser.add_argument("--chapter", required=True, help="Chapter id, for example ch01")
    parser.add_argument("--out", help="Output JSON path; defaults to chapters/chNN/image-tasks.json")
    parser.add_argument("--preferences", help="Explicit project preferences JSON; omit for legacy defaults")
    args = parser.parse_args()

    try:
        settings = load_production_settings(args.preferences)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    tasks = build_image_tasks(Path(args.storyboard), Path(args.visual_bible), args.chapter, settings=settings)
    output = Path(args.out) if args.out else Path("chapters") / args.chapter / "image-tasks.json"
    write_image_tasks(tasks, output)
    print(json.dumps({"tasks": len(tasks), "out": str(output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
