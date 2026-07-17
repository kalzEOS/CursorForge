from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cursorforge.models import CursorFrame
from cursorforge.scaler import ImageScaler, pick_source_frame, scale_hotspot


def _frame(size: int, xhot: int = 0, yhot: int = 0, order: int = 0) -> CursorFrame:
    return CursorFrame(
        size=size, xhot=xhot, yhot=yhot,
        image_path=Path(f"frame_{size}.png"),
        delay_ms=0, source_order=order,
    )


class TestPickSourceFrame:
    def test_picks_smallest_frame_at_or_above_target(self) -> None:
        frames = [_frame(24), _frame(32), _frame(48)]
        assert pick_source_frame(frames, 28).size == 32

    def test_exact_match(self) -> None:
        frames = [_frame(24), _frame(32), _frame(48)]
        assert pick_source_frame(frames, 32).size == 32

    def test_falls_back_to_largest_when_all_smaller(self) -> None:
        frames = [_frame(24), _frame(32)]
        assert pick_source_frame(frames, 64).size == 32

    def test_single_frame(self) -> None:
        frames = [_frame(32)]
        assert pick_source_frame(frames, 16).size == 32
        assert pick_source_frame(frames, 48).size == 32


class TestImageScaler:
    def test_scale_calls_magick(self, tmp_path: Path) -> None:
        src = tmp_path / "in.png"
        src.touch()
        dst = tmp_path / "out.png"
        scaler = ImageScaler()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = scaler.scale(src, dst, 48)
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "magick" in cmd
        assert "48x48!" in cmd

    def test_scale_returns_false_on_nonzero_exit(self, tmp_path: Path) -> None:
        src = tmp_path / "in.png"
        src.touch()
        dst = tmp_path / "out.png"
        scaler = ImageScaler()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            result = scaler.scale(src, dst, 48)
        assert result is False

    def test_scale_returns_false_when_magick_missing(self, tmp_path: Path) -> None:
        src = tmp_path / "in.png"
        src.touch()
        dst = tmp_path / "out.png"
        scaler = ImageScaler()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = scaler.scale(src, dst, 48)
        assert result is False
