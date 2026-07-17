from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cursorforge.extractor import CursorExtractor
from cursorforge.models import CursorFrame, ExtractedCursor
from cursorforge.validator import CursorValidator


def _frame(size: int) -> CursorFrame:
    return CursorFrame(
        size=size, xhot=0, yhot=0,
        image_path=Path(f"{size}.png"),
        delay_ms=0, source_order=0,
    )


def _mock_extractor(frames: list[CursorFrame] | None) -> CursorExtractor:
    ext = MagicMock(spec=CursorExtractor)
    if frames is None:
        ext.extract.return_value = None
    else:
        ext.extract.return_value = ExtractedCursor(
            original_path=Path("cursor"),
            frames=frames,
        )
    return ext


class TestCursorValidator:
    def test_ok_when_all_sizes_present(self, tmp_path: Path) -> None:
        extractor = _mock_extractor([_frame(32), _frame(48)])
        validator = CursorValidator(extractor=extractor)
        ok, missing = validator.validate(tmp_path / "cursor", frozenset({32, 48}))
        assert ok is True
        assert missing == set()

    def test_reports_missing_sizes(self, tmp_path: Path) -> None:
        extractor = _mock_extractor([_frame(32)])
        validator = CursorValidator(extractor=extractor)
        ok, missing = validator.validate(tmp_path / "cursor", frozenset({32, 48}))
        assert ok is False
        assert missing == {48}

    def test_extraction_failure_returns_all_missing(self, tmp_path: Path) -> None:
        extractor = _mock_extractor(None)
        validator = CursorValidator(extractor=extractor)
        ok, missing = validator.validate(tmp_path / "cursor", frozenset({32, 48}))
        assert ok is False
        assert missing == {32, 48}

    def test_superset_of_expected_is_ok(self, tmp_path: Path) -> None:
        extractor = _mock_extractor([_frame(24), _frame(32), _frame(48)])
        validator = CursorValidator(extractor=extractor)
        ok, missing = validator.validate(tmp_path / "cursor", frozenset({32}))
        assert ok is True
        assert missing == set()
