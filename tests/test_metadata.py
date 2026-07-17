from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from cursorforge.metadata import is_safe_output_name, read_theme_name, write_output_metadata


class TestMetadata:
    def test_read_existing_index_theme(self, tmp_path: Path) -> None:
        cfg = configparser.RawConfigParser()
        cfg["Icon Theme"] = {"Name": "My Theme"}
        with (tmp_path / "index.theme").open("w") as f:
            cfg.write(f)
        assert read_theme_name(tmp_path) == "My Theme"

    def test_missing_index_returns_none(self, tmp_path: Path) -> None:
        assert read_theme_name(tmp_path) is None

    def test_preserves_unrelated_keys(self, tmp_path: Path) -> None:
        cfg = configparser.RawConfigParser()
        cfg["Icon Theme"] = {"Name": "Old", "Example": "preserved_value"}
        with (tmp_path / "index.theme").open("w") as f:
            cfg.write(f)

        write_output_metadata(tmp_path, "New Name", "OldTheme")

        out = configparser.RawConfigParser()
        out.read(tmp_path / "index.theme", encoding="utf-8")
        assert out.get("Icon Theme", "Example") == "preserved_value"

    def test_updates_display_name(self, tmp_path: Path) -> None:
        write_output_metadata(tmp_path, "Generated Theme", "SourceTheme")
        out = configparser.RawConfigParser()
        out.read(tmp_path / "index.theme", encoding="utf-8")
        assert out.get("Icon Theme", "Name") == "Generated Theme"

    def test_safe_output_name_valid(self) -> None:
        assert is_safe_output_name("MyTheme-Multi")

    def test_safe_output_name_rejects_slash(self) -> None:
        assert not is_safe_output_name("bad/name")

    def test_safe_output_name_rejects_empty(self) -> None:
        assert not is_safe_output_name("")

    def test_creates_index_when_missing(self, tmp_path: Path) -> None:
        write_output_metadata(tmp_path, "Brand New", "Source")
        assert (tmp_path / "index.theme").is_file()
