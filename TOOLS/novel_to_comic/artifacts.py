"""UTF-8 JSON persistence for local production artifacts.

Writes replace one complete file atomically. Callers still own artifact schemas,
error reporting and coordination when several files form a production stage.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any


def read_json(path: str | Path) -> Any:
    """Read JSON without hiding filesystem, encoding or decoding failures."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    """Publish a complete JSON document, leaving an existing file intact on error.

    Existing file permissions and symlink destinations are preserved. New files
    use the temporary file's private permissions. The same-directory temporary
    file ensures replacement remains on the destination's filesystem.
    """
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    target = Path(path)
    if target.is_symlink():
        target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent,
    )
    temporary = Path(temporary_name)
    handle = None
    try:
        handle = os.fdopen(descriptor, "w", encoding="utf-8")
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, target)
    finally:
        if handle is None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
