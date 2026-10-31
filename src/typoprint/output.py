"""Atomic publication, separate from compilation."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from typoprint.models import RenderError, RenderResult


def write_pdf(result: RenderResult, destination: str | Path) -> Path:
    """Replace a destination only after a complete, flushed PDF is available."""
    target = Path(destination).resolve()
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            dir=target.parent, prefix=".typoprint-", delete=False
        ) as f:
            temporary = Path(f.name)
            f.write(result.content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, target)
    except OSError as error:
        raise RenderError(f"Cannot write PDF to {target}: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target
