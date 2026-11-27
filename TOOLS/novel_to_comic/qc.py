"""Basic filesystem and image QC for comic chapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


def qc_chapter(
    storyboard_path: str | Path,
    page_art_dir: str | Path | None,
    finished_pages_dir: str | Path,
    output_path: str | Path,
    expected_size: tuple[int, int] = (2480, 3508),
) -> dict[str, Any]:
    """Check finished pages, and fallback art only when explicitly requested.

    Pass ``None`` for ``page_art_dir`` for the normal image2 finished-page
    workflow. Existing callers that supply it retain both image checks.
    """
    storyboard = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    issues: list[dict[str, Any]] = []
    page_count = len(storyboard.get("pages", []))
    for page in storyboard.get("pages", []):
        page_number = int(page["page"])
        finished_path = Path(finished_pages_dir) / f"page-{page_number:03d}.png"
        if page_art_dir is not None:
            art_path = Path(page_art_dir) / f"page-{page_number:03d}.png"
            _check_image(issues, page_number, "page_art", art_path, expected_size)
        _check_image(issues, page_number, "finished_page", finished_path, expected_size)
        text_count = sum(len(panel.get("dialogue", [])) + len(panel.get("captions", [])) + len(panel.get("sfx", [])) for panel in page.get("panels", []))
        if text_count == 0:
            issues.append(
                {
                    "issue_id": f"page-{page_number:03d}-no-reader-text",
                    "severity": "medium",
                    "category": "lettering",
                    "status": "open",
                    "description": "Storyboard page has no dialogue, captions, or SFX.",
                }
            )

    blocking = [issue for issue in issues if issue["severity"] in {"high", "blocking"} and issue["status"] == "open"]
    report = {
        "chapter": Path(storyboard_path).parent.name,
        "page_count": page_count,
        "expected_size": {"width": expected_size[0], "height": expected_size[1]},
        "issues": issues,
        "blocking_open_issues": len(blocking),
        "status": "pass" if not blocking else "needs_fix",
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _check_image(
    issues: list[dict[str, Any]],
    page_number: int,
    kind: str,
    path: Path,
    expected_size: tuple[int, int],
) -> None:
    if not path.exists():
        issues.append(
            {
                "issue_id": f"page-{page_number:03d}-{kind}-missing",
                "severity": "blocking",
                "category": kind,
                "status": "open",
                "description": f"Missing {kind} image at {path}.",
            }
        )
        return
    try:
        with Image.open(path) as image:
            # Decoding catches truncated pixel data, including when the header
            # alone advertises the correct dimensions.
            image.load()
            if image.size != expected_size:
                issues.append(
                    {
                        "issue_id": f"page-{page_number:03d}-{kind}-wrong-size",
                        "severity": "high",
                        "category": kind,
                        "status": "open",
                        "description": f"{kind} is {image.size[0]}x{image.size[1]}, expected {expected_size[0]}x{expected_size[1]}.",
                    }
                )
            if kind == "page_art":
                with image.convert("RGB") as rgb:
                    coverage = _non_white_bbox_coverage(rgb)
                if coverage < 0.45:
                    issues.append(
                        {
                            "issue_id": f"page-{page_number:03d}-{kind}-large-margin",
                            "severity": "medium",
                            "category": kind,
                            "status": "open",
                            "description": f"Visible art coverage is {coverage:.2f}; generated image likely did not fill the A4 page.",
                        }
                    )
    except (OSError, Image.DecompressionBombError) as error:
        issues.append(
            {
                "issue_id": f"page-{page_number:03d}-{kind}-unreadable",
                "severity": "blocking",
                "category": kind,
                "status": "open",
                "description": f"Cannot read {kind} image at {path}: {error}.",
            }
        )


def _non_white_bbox_coverage(image: Image.Image) -> float:
    with Image.new("RGB", image.size, (255, 255, 255)) as white:
        with ImageChops.difference(image, white) as diff:
            bbox = diff.getbbox()
    if not bbox:
        return 0.0
    x0, y0, x1, y1 = bbox
    return ((x1 - x0) * (y1 - y0)) / (image.width * image.height)
