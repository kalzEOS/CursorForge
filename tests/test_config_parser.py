from __future__ import annotations

from pathlib import Path

import pytest

from cursorforge.inspector import CursorInspector


def _write_conf(tmp_path: Path, content: str) -> Path:
    conf = tmp_path / "test_cursor.conf"
    conf.write_text(content, encoding="utf-8")
    return conf


class TestConfigParser:
    def setup_method(self) -> None:
        self.inspector = CursorInspector()

    def test_static_cursor(self, tmp_path: Path) -> None:
        conf = _write_conf(tmp_path, "32 16 16 cursor_0001.png 0\n")
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 1
        assert frames[0].size == 32
        assert frames[0].xhot == 16
        assert frames[0].yhot == 16
        assert frames[0].delay_ms == 0

    def test_animated_cursor_multiple_frames(self, tmp_path: Path) -> None:
        conf = _write_conf(
            tmp_path,
            "32 16 16 frame_0001.png 100\n"
            "32 16 16 frame_0002.png 100\n"
            "32 16 16 frame_0003.png 100\n",
        )
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 3
        assert all(f.delay_ms == 100 for f in frames)

    def test_multiple_sizes(self, tmp_path: Path) -> None:
        conf = _write_conf(
            tmp_path,
            "24 12 12 cursor_24_0001.png 0\n"
            "32 16 16 cursor_32_0001.png 0\n"
            "48 24 24 cursor_48_0001.png 0\n",
        )
        frames = self.inspector._parse_conf(conf)
        sizes = {f.size for f in frames}
        assert sizes == {24, 32, 48}

    def test_comments_ignored(self, tmp_path: Path) -> None:
        conf = _write_conf(
            tmp_path,
            "# this is a comment\n"
            "32 16 16 cursor_0001.png 0\n",
        )
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 1

    def test_blank_lines_ignored(self, tmp_path: Path) -> None:
        conf = _write_conf(
            tmp_path,
            "\n32 16 16 cursor_0001.png 0\n\n",
        )
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 1

    def test_irregular_whitespace(self, tmp_path: Path) -> None:
        conf = _write_conf(tmp_path, "32\t16\t16\tcursor_0001.png\t0\n")
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 1
        assert frames[0].size == 32

    def test_missing_delay_defaults_to_zero(self, tmp_path: Path) -> None:
        conf = _write_conf(tmp_path, "32 16 16 cursor_0001.png\n")
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 1
        assert frames[0].delay_ms == 0

    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        conf = _write_conf(
            tmp_path,
            "not valid at all\n"
            "32 16 16 cursor_0001.png 0\n",
        )
        frames = self.inspector._parse_conf(conf)
        assert len(frames) == 1

    def test_source_order_increments(self, tmp_path: Path) -> None:
        conf = _write_conf(
            tmp_path,
            "32 16 16 a.png 0\n"
            "32 16 16 b.png 0\n"
            "32 16 16 c.png 0\n",
        )
        frames = self.inspector._parse_conf(conf)
        assert [f.source_order for f in frames] == [0, 1, 2]
