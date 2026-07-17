from __future__ import annotations

import logging
from pathlib import Path

from cursorforge.extractor import CursorExtractor
from cursorforge.models import CursorFrame, CursorTheme, ExtractedCursor

log = logging.getLogger(__name__)

_IMPORTANT_CURSORS = ["left_ptr", "default", "pointer", "text", "wait", "crosshair"]
_MAX_SAMPLE = 20


class CursorInspector:
    """Inspects cursor files using CursorExtractor to determine embedded sizes."""

    def __init__(self, extractor: CursorExtractor | None = None) -> None:
        self._extractor = extractor or CursorExtractor()

    def inspect_theme(
        self, theme: CursorTheme, max_files: int = _MAX_SAMPLE
    ) -> tuple[tuple[int, ...], str | None, int, int]:
        """Return (sizes, warning_or_None, inspected_count, failed_count)."""
        cursor_files = self._pick_cursor_files(theme.cursor_path, max_files)
        sizes_per_file: dict[str, frozenset[int]] = {}
        failed = 0

        for cursor_file in cursor_files:
            try:
                frames = self.inspect_cursor(cursor_file)
                if frames:
                    sizes_per_file[cursor_file.name] = frozenset(f.size for f in frames)
            except Exception as exc:
                log.warning("failed to inspect %s: %s", cursor_file.name, exc)
                failed += 1

        if not sizes_per_file:
            return (), None, 0, failed

        all_size_sets = list(sizes_per_file.values())
        union_sizes = tuple(sorted(frozenset().union(*all_size_sets)))

        warning: str | None = None
        if len(set(all_size_sets)) > 1:
            warning = (
                "Size sets differ across cursors. "
                "Showing union of all detected sizes."
            )

        return union_sizes, warning, len(sizes_per_file), failed

    def inspect_cursor(self, cursor_path: Path) -> list[CursorFrame]:
        """Extract frame metadata from a single cursor file."""
        extracted, tmpdir = self._extractor.extract_to_temp(cursor_path)
        with tmpdir:
            if extracted is None:
                return []
            return list(extracted.frames)

    def _pick_cursor_files(self, cursors_dir: Path, max_files: int) -> list[Path]:
        files: list[Path] = []
        for name in _IMPORTANT_CURSORS:
            candidate = cursors_dir / name
            if candidate.is_file():
                files.append(candidate)

        try:
            for entry in cursors_dir.iterdir():
                if entry.is_file() and entry.name not in _IMPORTANT_CURSORS:
                    files.append(entry)
                    if len(files) >= max_files:
                        break
        except PermissionError:
            pass

        return files[:max_files]


def sizes_from_frames(frames: list[CursorFrame]) -> tuple[int, ...]:
    return tuple(sorted({f.size for f in frames}))


def extracted_cursor_from_frames(
    original_path: Path, frames: list[CursorFrame]
) -> ExtractedCursor:
    return ExtractedCursor(original_path=original_path, frames=frames)
