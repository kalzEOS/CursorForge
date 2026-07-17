from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from cursorforge.models import CursorFrame, ExtractedCursor
from cursorforge.scaler import ImageScaler, scale_hotspot

log = logging.getLogger(__name__)


class CursorCompiler:
    """Compiles a set of scaled PNG frames into an Xcursor file using xcursorgen."""

    def __init__(self, scaler: ImageScaler | None = None) -> None:
        self._scaler = scaler or ImageScaler()

    def compile(
        self,
        extracted: ExtractedCursor,
        target_size: int,
        work_dir: Path,
        out_path: Path,
        timeout: int = 30,
    ) -> bool:
        """Scale frames and compile them into an Xcursor file at out_path.

        Returns True on success, False if scaling or xcursorgen fails.
        work_dir must exist; intermediate PNGs and the .conf are written there.
        """
        frames = extracted.frames
        if not frames:
            log.warning("no frames in %s", extracted.original_path.name)
            return False

        scaled = self._scaler.scale_frames(frames, target_size, work_dir)
        if scaled is None:
            log.warning("scaling failed for %s at size %d", extracted.original_path.name, target_size)
            return False

        conf_path = work_dir / f"{extracted.original_path.name}_{target_size}.conf"
        self._write_conf(conf_path, scaled, target_size)

        return self._run_xcursorgen(conf_path, out_path, timeout)

    def _write_conf(
        self,
        conf_path: Path,
        scaled: list[tuple[CursorFrame, Path]],
        target_size: int,
    ) -> None:
        lines: list[str] = []
        for frame, png_path in scaled:
            xhot, yhot = scale_hotspot(frame.xhot, frame.yhot, frame.size, target_size)
            if frame.delay_ms > 0:
                lines.append(f"{target_size} {xhot} {yhot} {png_path.name} {frame.delay_ms}")
            else:
                lines.append(f"{target_size} {xhot} {yhot} {png_path.name}")
        conf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def compile_augmented(
        self,
        extracted: ExtractedCursor,
        new_sizes: list[int],
        work_dir: Path,
        out_path: Path,
        timeout: int = 30,
    ) -> bool:
        """Compile an Xcursor file that contains all existing sizes PLUS new_sizes.

        Existing frames are re-used as-is from their extracted PNG paths.
        New sizes are scaled from the best available source frame.
        Returns True on success, False on any failure.
        """
        frames = extracted.frames
        if not frames:
            log.warning("no frames in %s", extracted.original_path.name)
            return False

        conf_lines: list[str] = []

        # Existing frames — keep their original PNGs verbatim
        for frame in frames:
            xhot, yhot = frame.xhot, frame.yhot
            if frame.delay_ms > 0:
                conf_lines.append(
                    f"{frame.size} {xhot} {yhot} {frame.image_path} {frame.delay_ms}"
                )
            else:
                conf_lines.append(f"{frame.size} {xhot} {yhot} {frame.image_path}")

        # New sizes — scale from best source frame
        existing_sizes = {f.size for f in frames}
        for new_size in new_sizes:
            if new_size in existing_sizes:
                continue
            scaled = self._scaler.scale_frames(frames, new_size, work_dir)
            if scaled is None:
                log.warning(
                    "scaling failed for %s at size %d",
                    extracted.original_path.name,
                    new_size,
                )
                return False
            for _frame, png_path in scaled:
                xhot, yhot = scale_hotspot(_frame.xhot, _frame.yhot, _frame.size, new_size)
                delay = _frame.delay_ms
                if delay > 0:
                    conf_lines.append(f"{new_size} {xhot} {yhot} {png_path} {delay}")
                else:
                    conf_lines.append(f"{new_size} {xhot} {yhot} {png_path}")

        conf_path = work_dir / f"{extracted.original_path.name}.conf"
        conf_path.write_text("\n".join(conf_lines) + "\n", encoding="utf-8")
        return self._run_xcursorgen(conf_path, out_path, timeout)

    def _run_xcursorgen(self, conf_path: Path, out_path: Path, timeout: int) -> bool:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ["xcursorgen", str(conf_path), str(out_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                log.warning(
                    "xcursorgen failed for %s: %s",
                    conf_path.name,
                    result.stderr.strip(),
                )
                return False
            return True
        except FileNotFoundError:
            log.error("xcursorgen not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            log.warning("xcursorgen timed out for %s", conf_path.name)
            return False
