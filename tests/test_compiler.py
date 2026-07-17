from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cursorforge.compiler import CursorCompiler
from cursorforge.models import CursorFrame, ExtractedCursor
from cursorforge.scaler import ImageScaler


def _frame(size: int, xhot: int = 8, yhot: int = 8, delay: int = 0, order: int = 0) -> CursorFrame:
    return CursorFrame(
        size=size, xhot=xhot, yhot=yhot,
        image_path=Path(f"frame_{size}_{order}.png"),
        delay_ms=delay, source_order=order,
    )


def _extracted(tmp_path: Path, frames: list[CursorFrame]) -> ExtractedCursor:
    return ExtractedCursor(original_path=tmp_path / "left_ptr", frames=frames)


class TestCursorCompiler:
    def _mock_scaler(self, tmp_path: Path, frames: list[CursorFrame]) -> ImageScaler:
        scaler = MagicMock(spec=ImageScaler)
        scaled_pairs = []
        for i, f in enumerate(frames):
            png = tmp_path / f"frame_{i:04d}_48.png"
            png.touch()
            scaled_pairs.append((f, png))
        scaler.scale_frames.return_value = scaled_pairs
        return scaler

    def test_compile_writes_conf_and_calls_xcursorgen(self, tmp_path: Path) -> None:
        frames = [_frame(32)]
        extracted = _extracted(tmp_path, frames)
        scaler = self._mock_scaler(tmp_path, frames)
        compiler = CursorCompiler(scaler=scaler)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            out = tmp_path / "cursors" / "left_ptr"
            result = compiler.compile(extracted, 48, tmp_path, out)

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "xcursorgen" in cmd

    def test_compile_returns_false_on_empty_frames(self, tmp_path: Path) -> None:
        extracted = _extracted(tmp_path, [])
        compiler = CursorCompiler()
        result = compiler.compile(extracted, 48, tmp_path, tmp_path / "out")
        assert result is False

    def test_compile_returns_false_when_scaling_fails(self, tmp_path: Path) -> None:
        frames = [_frame(32)]
        extracted = _extracted(tmp_path, frames)
        scaler = MagicMock(spec=ImageScaler)
        scaler.scale_frames.return_value = None
        compiler = CursorCompiler(scaler=scaler)
        result = compiler.compile(extracted, 48, tmp_path, tmp_path / "out")
        assert result is False

    def test_conf_content_static(self, tmp_path: Path) -> None:
        frames = [_frame(32, xhot=10, yhot=12)]
        extracted = _extracted(tmp_path, frames)
        scaler = self._mock_scaler(tmp_path, frames)
        compiler = CursorCompiler(scaler=scaler)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            compiler.compile(extracted, 48, tmp_path, tmp_path / "out")

        conf_files = list(tmp_path.glob("*.conf"))
        assert len(conf_files) == 1
        lines = [l for l in conf_files[0].read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        parts = lines[0].split()
        assert parts[0] == "48"

    def test_conf_content_animated(self, tmp_path: Path) -> None:
        frames = [_frame(32, delay=100, order=i) for i in range(3)]
        extracted = _extracted(tmp_path, frames)
        scaler = self._mock_scaler(tmp_path, frames)
        compiler = CursorCompiler(scaler=scaler)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            compiler.compile(extracted, 48, tmp_path, tmp_path / "out")

        conf_files = list(tmp_path.glob("*.conf"))
        lines = [l for l in conf_files[0].read_text().splitlines() if l.strip()]
        assert len(lines) == 3
        for line in lines:
            parts = line.split()
            assert parts[-1] == "100"
