"""Optional fallback for composing separate panel images into page images.

The production v0 flow asks image2 for complete pages. This module is useful
for layout previews, tests, or recovery when a page must be rebuilt from
separate panels.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from .layout import panel_boxes


DEFAULT_PAGE_SIZE = (2480, 3508)


def compose_chapter_pages(
    storyboard_path: str | Path,
    finals_dir: str | Path,
    output_dir: str | Path,
    page_size: tuple[int, int] = DEFAULT_PAGE_SIZE,
    gutter: int = 8,
) -> list[Path]:
    storyboard = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    finals = Path(finals_dir)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    page_paths: list[Path] = []

    for page in storyboard.get("pages", []):
        page_number = int(page["page"])
        canvas = Image.new("RGB", page_size, "white")
        boxes = panel_boxes(page.get("layout", "2x2"), page_size, gutter, len(page.get("panels", [])))
        for panel, box in zip(page.get("panels", []), boxes, strict=False):
            panel_number = int(panel["panel"])
            panel_image = _load_panel_image(finals / f"p{page_number:03d}-{panel_number:02d}.png", box)
            canvas.paste(panel_image, box[:2])
        page_path = target / f"page-{page_number:03d}.png"
        canvas.save(page_path)
        page_paths.append(page_path)

    return page_paths


def _load_panel_image(path: Path, box: tuple[int, int, int, int]) -> Image.Image:
    width = box[2] - box[0]
    height = box[3] - box[1]
    if not path.exists():
        placeholder = Image.new("RGB", (width, height), (245, 245, 245))
        draw = ImageDraw.Draw(placeholder)
        draw.rectangle((0, 0, width - 1, height - 1), outline=(180, 180, 180), width=2)
        draw.text((12, 12), path.name, fill=(80, 80, 80))
        return placeholder

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((width, height))
        panel = Image.new("RGB", (width, height), "white")
        x = (width - rgb.width) // 2
        y = (height - rgb.height) // 2
        panel.paste(rgb, (x, y))
        return panel
