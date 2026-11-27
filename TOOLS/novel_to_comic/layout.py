"""Pure panel geometry shared by composition and fallback lettering.

Callers own the visual policy: composition fills the canvas, while lettering
keeps a safe margin. Keeping those values explicit avoids conflating the two.
"""

from __future__ import annotations


def panel_boxes(
    layout: str,
    page_size: tuple[int, int],
    gutter: int,
    panel_count: int,
    *,
    margin: int = 0,
) -> list[tuple[int, int, int, int]]:
    """Return row-major panel rectangles within the caller's content area."""
    width, height = page_size
    content = (margin, margin, width - margin, height - margin)
    if layout == "splash":
        return [content]
    if layout == "3x2":
        rows, cols = 3, 2
    elif layout == "2x2":
        rows, cols = 2, 2
    else:
        cols = 2
        rows = max(1, (panel_count + 1) // 2)

    content_width = width - 2 * margin
    content_height = height - 2 * margin
    cell_width = (content_width - gutter * (cols - 1)) // cols
    cell_height = (content_height - gutter * (rows - 1)) // rows
    boxes: list[tuple[int, int, int, int]] = []
    for row in range(rows):
        for col in range(cols):
            x0 = margin + col * (cell_width + gutter)
            y0 = margin + row * (cell_height + gutter)
            boxes.append((x0, y0, x0 + cell_width, y0 + cell_height))
    return boxes[:panel_count]
