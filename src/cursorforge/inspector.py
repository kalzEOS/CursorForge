from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from cursorforge.models import CursorFrame, CursorTheme, ExtractedCursor

log = logging.getLogger(__name__)

_IMPORTANT_CURSORS = ["left_ptr", "default", "pointer", "text", "wait", "crosshair"]
_MAX_SAMPLE = 20


class CursorInspector:
    """Inspects cursor files using xcur2png to determine embedded sizes."""

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
        with tempfile.TemporaryDirectory(prefix="cursorforge_inspect_") as tmpdir:
            tmp = Path(tmpdir)
            conf_path = self._run_xcur2png(cursor_path, tmp)
            if conf_path is None:
                return []
            return self._parse_conf(conf_path)

    def _pick_cursor_files(self, cursors_dir: Path, max_files: int) -> list[Path]:
        files: list[Path] = []
        # prioritize important cursors first
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

    def _run_xcur2png(self, cursor_path: Path, workdir: Path) -> Path | None:
        try:
            result = subprocess.run(
                ["xcur2png", str(cursor_path)],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=15,
            )
            log.debug(
                "xcur2png %s exit=%d", cursor_path.name, result.returncode
            )
            if result.returncode != 0:
                log.warning(
                    "xcur2png failed for %s: %s", cursor_path.name, result.stderr.strip()
                )
                return None
        except FileNotFoundError:
            log.error("xcur2png not found in PATH")
            return None
        except subprocess.TimeoutExpired:
            log.warning("xcur2png timed out for %s", cursor_path.name)
            return None

        conf_files = list(workdir.glob("*.conf"))
        if not conf_files:
            log.warning("xcur2png produced no .conf for %s", cursor_path.name)
            return None
        return conf_files[0]

    def _parse_conf(self, conf_path: Path) -> list[CursorFrame]:
        frames: list[CursorFrame] = []
        try:
            text = conf_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.warning("cannot read conf %s: %s", conf_path, exc)
            return []

        order = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 4:
                log.debug("skipping malformed conf line: %r", line)
                continue
            try:
                size = int(parts[0])
                xhot = int(parts[1])
                yhot = int(parts[2])
                image_path = conf_path.parent / parts[3]
                delay_ms = int(parts[4]) if len(parts) >= 5 else 0
                frames.append(CursorFrame(
                    size=size,
                    xhot=xhot,
                    yhot=yhot,
                    image_path=image_path,
                    delay_ms=delay_ms,
                    source_order=order,
                ))
                order += 1
            except (ValueError, IndexError) as exc:
                log.debug("malformed conf line %r: %s", line, exc)

        return frames


def sizes_from_frames(frames: list[CursorFrame]) -> tuple[int, ...]:
    return tuple(sorted({f.size for f in frames}))


def extracted_cursor_from_frames(
    original_path: Path, frames: list[CursorFrame]
) -> ExtractedCursor:
    return ExtractedCursor(original_path=original_path, frames=frames)
