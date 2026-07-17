from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from cursorforge.extractor import CursorExtractor

log = logging.getLogger(__name__)


class CursorValidator:
    """Verifies that a compiled Xcursor file contains the expected sizes."""

    def __init__(self, extractor: CursorExtractor | None = None) -> None:
        self._extractor = extractor or CursorExtractor()

    def validate(self, cursor_path: Path, expected_sizes: frozenset[int]) -> tuple[bool, set[int]]:
        """Extract the cursor and check it contains all expected_sizes.

        Returns (ok, missing_sizes). ok is True when missing_sizes is empty.
        """
        with tempfile.TemporaryDirectory(prefix="cursorforge_validate_") as tmpdir:
            extracted = self._extractor.extract(cursor_path, Path(tmpdir))
            if extracted is None:
                log.warning("validation extraction failed for %s", cursor_path.name)
                return False, set(expected_sizes)

            found = {f.size for f in extracted.frames}
            missing = set(expected_sizes) - found
            if missing:
                log.warning(
                    "%s missing sizes after compile: %s",
                    cursor_path.name,
                    sorted(missing),
                )
            return len(missing) == 0, missing
