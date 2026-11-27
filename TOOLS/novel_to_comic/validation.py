"""Shared file diagnostics and report envelopes for page documents.

Domain rules stay in the individual validators. This module owns only the
boundary from JSON files to data and the stable page-validation report shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import read_json


Issue = dict[str, str]


def read_document(path: Path, kind: str) -> tuple[Any, list[Issue]]:
    """Read JSON, turning recoverable input failures into validator issues."""
    try:
        return read_json(path), []
    except FileNotFoundError:
        message = f"{kind} not found"
    except json.JSONDecodeError as error:
        message = f"invalid JSON: {error.msg}"
    except UnicodeDecodeError as error:
        message = f"invalid UTF-8: {error.reason}"
    except OSError as error:
        message = f"cannot read {kind}: {error.strerror or str(error)}"
    return None, [{"file": str(path), "issue": message}]


def has_text(value: Any) -> bool:
    """Whether a required text field contains more than whitespace."""
    return isinstance(value, str) and bool(value.strip())


def page_report(path: Path, document: dict[str, Any], issues: list[Issue], **counts: int) -> dict[str, Any]:
    """Keep page counts and the public diagnostic envelope consistent."""
    pages = document.get("pages") if isinstance(document.get("pages"), list) else []
    return {
        "path": str(path),
        "status": "pass" if not issues else "needs_fix",
        "actual_page_count": len(pages),
        "declared_page_count": document.get("actual_page_count"),
        **counts,
        "issues": issues,
    }
