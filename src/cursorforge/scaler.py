from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from cursorforge.models import CursorFrame

log = logging.getLogger(__name__)


def pick_source_frame(frames: list[CursorFrame], target_size: int) -> CursorFrame:
    """Return the best frame to use as a scaling source for target_size.

    Prefers the smallest frame that is >= target_size (downscale is sharper);
    falls back to the largest available frame when all are smaller.
    """
    candidates = [f for f in frames if f.size >= target_size]
    if candidates:
        return min(candidates, key=lambda f: f.size)
    return max(frames, key=lambda f: f.size)


def scale_hotspot(xhot: int, yhot: int, src_size: int, dst_size: int) -> tuple[int, int]:
    """Proportionally scale a hotspot coordinate from src_size to dst_size.

    Result is clamped to [0, dst_size - 1] to keep the hotspot inside the frame.
    """
    if src_size == 0:
        return 0, 0
    ratio = dst_size / src_size
    nx = max(0, min(dst_size - 1, round(xhot * ratio)))
    ny = max(0, min(dst_size - 1, round(yhot * ratio)))
    return nx, ny


class ImageScaler:
    """Scales PNG frames to a target size using ImageMagick (magick)."""

    def scale(
        self,
        source: Path,
        dest: Path,
        target_size: int,
        timeout: int = 30,
    ) -> bool:
        """Scale source PNG to target_size x target_size, writing to dest.

        Returns True on success, False on failure.
        """
        try:
            result = subprocess.run(
                [
                    "magick",
                    str(source),
                    "-resize",
                    f"{target_size}x{target_size}!",
                    "-filter",
                    "Lanczos",
                    str(dest),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                log.warning(
                    "magick failed scaling %s → %s: %s",
                    source.name,
                    dest.name,
                    result.stderr.strip(),
                )
                return False
            return True
        except FileNotFoundError:
            log.error("magick not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            log.warning("magick timed out scaling %s", source.name)
            return False

    def scale_frames(
        self,
        frames: list[CursorFrame],
        target_size: int,
        out_dir: Path,
    ) -> list[tuple[CursorFrame, Path]] | None:
        """Scale all unique-delay frames for an animated cursor to target_size.

        Returns a list of (original_frame, scaled_png_path) pairs ordered by
        source_order, or None if any scaling operation fails.

        For static cursors (single frame or all delay_ms == 0) only one image
        is produced regardless of how many frames share the same pixel data.
        """
        source_frame = pick_source_frame(frames, target_size)
        nx, ny = scale_hotspot(source_frame.xhot, source_frame.yhot, source_frame.size, target_size)

        results: list[tuple[CursorFrame, Path]] = []
        for i, frame in enumerate(frames):
            out_name = f"frame_{i:04d}_{target_size}.png"
            out_path = out_dir / out_name
            src = pick_source_frame([frame], target_size)
            ok = self.scale(src.image_path, out_path, target_size)
            if not ok:
                return None
            results.append((frame, out_path))

        return results
