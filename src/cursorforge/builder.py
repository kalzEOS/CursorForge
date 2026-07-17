from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from cursorforge.compiler import CursorCompiler
from cursorforge.extractor import CursorExtractor
from cursorforge.metadata import write_output_metadata
from cursorforge.models import CursorTheme
from cursorforge.validator import CursorValidator

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, int], None]


@dataclass
class BuildResult:
    success: bool
    output_path: Path
    sizes_added: list[int] = field(default_factory=list)
    cursors_processed: int = 0
    cursors_failed: int = 0
    errors: list[str] = field(default_factory=list)


class ThemeBuilder:
    """Orchestrates extraction, scaling, compilation, and validation for a theme build."""

    def __init__(
        self,
        extractor: CursorExtractor | None = None,
        compiler: CursorCompiler | None = None,
        validator: CursorValidator | None = None,
    ) -> None:
        self._extractor = extractor or CursorExtractor()
        self._compiler = compiler or CursorCompiler()
        self._validator = validator or CursorValidator(extractor=self._extractor)

    def build(
        self,
        theme: CursorTheme,
        new_sizes: list[int],
        output_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> BuildResult:
        """Build a new theme at output_path with all existing sizes + new_sizes.

        on_progress(message, current, total) is called periodically if provided.
        """
        result = BuildResult(success=False, output_path=output_path)

        if not new_sizes:
            result.errors.append("No new sizes requested.")
            return result

        cursor_files = self._collect_cursor_files(theme.cursor_path)
        if not cursor_files:
            result.errors.append(f"No cursor files found in {theme.cursor_path}")
            return result

        out_cursors = output_path / "cursors"
        out_cursors.mkdir(parents=True, exist_ok=True)

        total = len(cursor_files)
        for i, entry in enumerate(cursor_files):
            if on_progress:
                on_progress(f"Processing {entry.name}…", i, total)

            if entry.is_symlink():
                self._copy_symlink(entry, out_cursors / entry.name)
                continue

            ok = self._process_cursor(entry, new_sizes, out_cursors, result)
            if ok:
                result.cursors_processed += 1
            else:
                result.cursors_failed += 1

        if on_progress:
            on_progress("Writing theme metadata…", total, total)

        write_output_metadata(
            output_path,
            display_name=output_path.name,
            source_name=theme.directory_name,
        )

        result.sizes_added = new_sizes
        result.success = result.cursors_failed == 0 or result.cursors_processed > 0
        return result

    def _collect_cursor_files(self, cursors_dir: Path) -> list[Path]:
        try:
            return sorted(cursors_dir.iterdir(), key=lambda p: p.name)
        except (PermissionError, FileNotFoundError) as exc:
            log.warning("cannot list cursors dir %s: %s", cursors_dir, exc)
            return []

    def _process_cursor(
        self,
        cursor_file: Path,
        new_sizes: list[int],
        out_cursors: Path,
        result: BuildResult,
    ) -> bool:
        with tempfile.TemporaryDirectory(prefix="cursorforge_build_") as tmpdir:
            tmp = Path(tmpdir)
            extracted = self._extractor.extract(cursor_file, tmp)
            if extracted is None:
                msg = f"Failed to extract {cursor_file.name}"
                log.warning(msg)
                result.errors.append(msg)
                return False

            existing_sizes = frozenset(f.size for f in extracted.frames)
            truly_new = [s for s in new_sizes if s not in existing_sizes]

            out_file = out_cursors / cursor_file.name
            ok = self._compiler.compile_augmented(
                extracted,
                truly_new,
                tmp,
                out_file,
            )
            if not ok:
                msg = f"Failed to compile {cursor_file.name}"
                log.warning(msg)
                result.errors.append(msg)
                return False

            expected = existing_sizes | frozenset(truly_new)
            valid, missing = self._validator.validate(out_file, frozenset(expected))
            if not valid:
                log.warning(
                    "%s validated with missing sizes: %s", cursor_file.name, sorted(missing)
                )

        return True

    def _copy_symlink(self, src: Path, dest: Path) -> None:
        try:
            target = src.readlink()
            if dest.exists() or dest.is_symlink():
                dest.unlink()
            dest.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            log.warning("could not copy symlink %s: %s", src.name, exc)
