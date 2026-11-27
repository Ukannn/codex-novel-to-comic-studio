"""Validation of whole-page director briefs before image generation."""

from __future__ import annotations

from pathlib import Path

from .validation import Issue


REQUIRED_MARKERS = [
    "Page purpose",
    "Source trace",
    "Reference lock",
    "Page layout",
    "Panel directives",
    "Text directives",
    "Image2 prompt",
    "QC checklist",
    "finished-pages/page-",
]


def validate_director_brief(text: str, *, path: str | Path = "<memory>") -> list[Issue]:
    """Return ordered diagnostics for one brief without file access."""
    issues: list[Issue] = []
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            issues.append({"file": str(path), "issue": f"missing marker: {marker}"})
    if "visual-bible/characters/" not in text and "No character reference required" not in text:
        issues.append({"file": str(path), "issue": "missing character reference lock or explicit no-character statement"})
    if "2x2" in text or "3x2" in text:
        issues.append({"file": str(path), "issue": "mechanical grid token found; describe manga panel geometry instead"})
    if "Do not draw text" in text or "no text" in text.lower():
        issues.append({"file": str(path), "issue": "finished-page brief must include exact readable text, not forbid all text"})
    return issues


def check_briefs(root: str | Path) -> dict[str, object]:
    directory = Path(root)
    files = sorted(directory.glob("page-*-director-brief.md"))
    issues: list[Issue] = []
    if not files:
        issues.append({"file": str(directory), "issue": "no director brief files found"})
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            issues.append({"file": str(path), "issue": f"invalid UTF-8: {error.reason}"})
            continue
        except OSError as error:
            issues.append({"file": str(path), "issue": f"cannot read director brief: {error.strerror or str(error)}"})
            continue
        issues.extend(validate_director_brief(text, path=path))
    return {"briefs": len(files), "issues": issues, "status": "pass" if not issues else "needs_fix"}
