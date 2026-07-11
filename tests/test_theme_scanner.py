from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from cursorforge.models import ThemeSource
from cursorforge.scanner import ThemeScanner


def _make_theme(tmp_path: Path, name: str, with_cursor: bool = True) -> Path:
    theme_dir = tmp_path / name
    cursors = theme_dir / "cursors"
    cursors.mkdir(parents=True)
    if with_cursor:
        (cursors / "left_ptr").write_bytes(b"\x00" * 8)
    return theme_dir


def _write_index(theme_dir: Path, display_name: str) -> None:
    cfg = configparser.RawConfigParser()
    cfg["Icon Theme"] = {"Name": display_name}
    with (theme_dir / "index.theme").open("w") as f:
        cfg.write(f)


class TestThemeScanner:
    def test_valid_theme_detected(self, tmp_path: Path) -> None:
        _make_theme(tmp_path, "MyTheme")
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.USER_ICONS)
        assert len(themes) == 1
        assert themes[0].directory_name == "MyTheme"

    def test_missing_cursors_directory_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "NoCursors").mkdir()
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.USER_ICONS)
        assert themes == []

    def test_empty_cursors_directory_excluded(self, tmp_path: Path) -> None:
        _make_theme(tmp_path, "EmptyTheme", with_cursor=False)
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.USER_ICONS)
        assert themes == []

    def test_metadata_name_used_when_present(self, tmp_path: Path) -> None:
        theme_dir = _make_theme(tmp_path, "dir-name")
        _write_index(theme_dir, "Pretty Display Name")
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.USER_ICONS)
        assert themes[0].name == "Pretty Display Name"

    def test_directory_name_fallback(self, tmp_path: Path) -> None:
        _make_theme(tmp_path, "fallback-theme")
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.USER_ICONS)
        assert themes[0].name == "fallback-theme"

    def test_source_type_preserved(self, tmp_path: Path) -> None:
        _make_theme(tmp_path, "T")
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.SYSTEM)
        assert themes[0].source_type == ThemeSource.SYSTEM

    def test_duplicate_display_names_both_returned(self, tmp_path: Path) -> None:
        for d in ("ThemeA", "ThemeB"):
            theme_dir = _make_theme(tmp_path, d)
            _write_index(theme_dir, "Same Name")
        scanner = ThemeScanner()
        themes = scanner._scan_directory(tmp_path, ThemeSource.USER_ICONS)
        assert len(themes) == 2
        assert all(t.name == "Same Name" for t in themes)

    def test_scan_deduplicates_by_resolved_path(self, tmp_path: Path) -> None:
        base_a = tmp_path / "a"
        base_b = tmp_path / "b"
        base_a.mkdir()
        base_b.mkdir()
        theme_dir = _make_theme(base_a, "Theme")
        (base_b / "Theme").symlink_to(theme_dir)

        scanner = ThemeScanner()
        themes = scanner.scan(search_paths=[
            (base_a, ThemeSource.USER_ICONS),
            (base_b, ThemeSource.USER_LOCAL_SHARE),
        ])

        assert len(themes) == 1
