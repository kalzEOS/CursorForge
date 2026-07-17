from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cursorforge.builder import BuildResult, ThemeBuilder
from cursorforge.compiler import CursorCompiler
from cursorforge.extractor import CursorExtractor
from cursorforge.models import CursorFrame, CursorTheme, ExtractedCursor, ThemeSource
from cursorforge.validator import CursorValidator


def _frame(size: int) -> CursorFrame:
    return CursorFrame(
        size=size, xhot=8, yhot=8,
        image_path=Path(f"{size}.png"),
        delay_ms=0, source_order=0,
    )


def _theme(tmp_path: Path) -> CursorTheme:
    cursors_dir = tmp_path / "cursors"
    cursors_dir.mkdir()
    (cursors_dir / "left_ptr").write_bytes(b"\x00" * 4)
    (cursors_dir / "arrow").symlink_to("left_ptr")
    return CursorTheme(
        name="TestTheme",
        directory_name="TestTheme",
        path=tmp_path,
        cursor_path=cursors_dir,
        source_type=ThemeSource.USER_LOCAL_SHARE,
        existing_sizes=(32,),
        inspected_files=1,
        failed_inspections=0,
    )


def _mock_extractor(frames: list[CursorFrame]) -> CursorExtractor:
    ext = MagicMock(spec=CursorExtractor)
    ext.extract.return_value = ExtractedCursor(
        original_path=Path("left_ptr"), frames=frames
    )
    return ext


def _mock_compiler(success: bool = True) -> CursorCompiler:
    comp = MagicMock(spec=CursorCompiler)
    comp.compile_augmented.return_value = success
    return comp


def _mock_validator(ok: bool = True) -> CursorValidator:
    val = MagicMock(spec=CursorValidator)
    val.validate.return_value = (ok, set())
    return val


class TestThemeBuilder:
    def test_successful_build(self, tmp_path: Path) -> None:
        theme = _theme(tmp_path)
        extractor = _mock_extractor([_frame(32)])
        compiler = _mock_compiler(True)
        validator = _mock_validator(True)

        output = tmp_path / "output" / "TestTheme-Multi"
        builder = ThemeBuilder(extractor=extractor, compiler=compiler, validator=validator)
        result = builder.build(theme, [48], output)

        assert result.success
        assert result.cursors_processed == 1
        assert result.cursors_failed == 0
        assert (output / "index.theme").is_file()

    def test_symlinks_are_copied(self, tmp_path: Path) -> None:
        theme = _theme(tmp_path)
        extractor = _mock_extractor([_frame(32)])
        compiler = _mock_compiler(True)
        validator = _mock_validator(True)

        output = tmp_path / "output" / "TestTheme-Multi"
        builder = ThemeBuilder(extractor=extractor, compiler=compiler, validator=validator)
        builder.build(theme, [48], output)

        arrow = output / "cursors" / "arrow"
        assert arrow.is_symlink()
        assert arrow.readlink() == Path("left_ptr")

    def test_no_new_sizes_returns_failure(self, tmp_path: Path) -> None:
        theme = _theme(tmp_path)
        builder = ThemeBuilder()
        result = builder.build(theme, [], tmp_path / "out")
        assert not result.success
        assert result.errors

    def test_extraction_failure_counts_as_failed(self, tmp_path: Path) -> None:
        theme = _theme(tmp_path)
        extractor = MagicMock(spec=CursorExtractor)
        extractor.extract.return_value = None
        compiler = _mock_compiler(True)
        validator = _mock_validator(True)

        output = tmp_path / "output" / "TestTheme-Multi"
        builder = ThemeBuilder(extractor=extractor, compiler=compiler, validator=validator)
        result = builder.build(theme, [48], output)

        assert result.cursors_failed == 1
        assert result.cursors_processed == 0

    def test_compile_failure_counts_as_failed(self, tmp_path: Path) -> None:
        theme = _theme(tmp_path)
        extractor = _mock_extractor([_frame(32)])
        compiler = _mock_compiler(False)
        validator = _mock_validator(True)

        output = tmp_path / "output" / "TestTheme-Multi"
        builder = ThemeBuilder(extractor=extractor, compiler=compiler, validator=validator)
        result = builder.build(theme, [48], output)

        assert result.cursors_failed == 1
        assert result.cursors_processed == 0

    def test_progress_callback_called(self, tmp_path: Path) -> None:
        theme = _theme(tmp_path)
        extractor = _mock_extractor([_frame(32)])
        compiler = _mock_compiler(True)
        validator = _mock_validator(True)

        calls: list[str] = []
        def on_progress(msg: str, current: int, total: int) -> None:
            calls.append(msg)

        output = tmp_path / "output" / "TestTheme-Multi"
        builder = ThemeBuilder(extractor=extractor, compiler=compiler, validator=validator)
        builder.build(theme, [48], output, on_progress=on_progress)

        assert len(calls) >= 2
        assert any("metadata" in c.lower() for c in calls)

    def test_empty_cursors_dir_returns_failure(self, tmp_path: Path) -> None:
        cursors_dir = tmp_path / "empty_theme" / "cursors"
        cursors_dir.mkdir(parents=True)
        theme = CursorTheme(
            name="Empty",
            directory_name="Empty",
            path=tmp_path / "empty_theme",
            cursor_path=cursors_dir,
            source_type=ThemeSource.USER_LOCAL_SHARE,
            existing_sizes=(),
            inspected_files=0,
            failed_inspections=0,
        )
        builder = ThemeBuilder()
        result = builder.build(theme, [48], tmp_path / "out")
        assert not result.success
        assert result.errors
