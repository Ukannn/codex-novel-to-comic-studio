#!/usr/bin/env python3
"""Validate whole-page manga director briefs before image2 generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_to_comic.director_briefs import REQUIRED_MARKERS, check_briefs


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate manga page director briefs.")
    parser.add_argument("director_briefs", help="Directory containing page-NNN-director-brief.md files")
    args = parser.parse_args()
    result = check_briefs(Path(args.director_briefs))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
