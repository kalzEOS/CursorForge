from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from cursorforge.models import CursorFrame, ExtractedCursor

log = logging.getLogger(__name__)


class CursorExtractor:
    """Extracts a compiled Xcursor file into PNG frames using xcur2png."""

    def extract(self, cursor_path: Path, work_dir: Path) -> ExtractedCursor | None:
        """
        Run xcur2png in work_dir and parse the resulting .conf.
        Returns None if extraction fails.
        Image paths in the returned frames are absolute and valid within work_dir.
        """
        conf_path = self._run_xcur2png(cursor_path, work_dir)
        if conf_path is None:
            return None
        frames = self.parse_conf(conf_path)
        if not frames:
            log.warning("xcur2png produced no frames for %s", cursor_path.name)
            return None
        return ExtractedCursor(original_path=cursor_path, frames=frames)

    def extract_to_temp(self, cursor_path: Path) -> tuple[ExtractedCursor | None, tempfile.TemporaryDirectory[str]]:
        """
        Extract into a fresh temp directory.
        Caller is responsible for cleaning up the returned TemporaryDirectory.
        """
        tmpdir = tempfile.TemporaryDirectory(prefix="cursorforge_extract_")
        result = self.extract(cursor_path, Path(tmpdir.name))
        return result, tmpdir

    def _run_xcur2png(self, cursor_path: Path, work_dir: Path) -> Path | None:
        try:
            result = subprocess.run(
                ["xcur2png", str(cursor_path)],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            log.debug("xcur2png %s exit=%d", cursor_path.name, result.returncode)
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

        conf_files = list(work_dir.glob("*.conf"))
        if not conf_files:
            log.warning("xcur2png produced no .conf for %s", cursor_path.name)
            return None
        return conf_files[0]

    def parse_conf(self, conf_path: Path) -> list[CursorFrame]:
        """Parse an xcur2png-generated .conf file into CursorFrame objects."""
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
