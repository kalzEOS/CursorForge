from __future__ import annotations

import configparser
import logging
from pathlib import Path

from cursorforge.models import CursorTheme, ThemeSource
import cursorforge.paths as _paths

log = logging.getLogger(__name__)


class ThemeScanner:
    def scan(
        self,
        search_paths: list[tuple[Path, ThemeSource]] | None = None,
    ) -> list[CursorTheme]:
        paths = search_paths if search_paths is not None else _paths.SEARCH_PATHS
        seen: dict[Path, CursorTheme] = {}
        for base, source in paths:
            if not base.is_dir():
                continue
            for theme in self._scan_directory(base, source):
                resolved = theme.path.resolve()
                if resolved not in seen:
                    seen[resolved] = theme
                    log.info("found theme %r at %s", theme.name, theme.path)
                else:
                    log.debug("skipping duplicate %s -> %s", theme.path, resolved)
        return sorted(seen.values(), key=lambda t: t.name.lower())

    def _scan_directory(self, base: Path, source: ThemeSource) -> list[CursorTheme]:
        results: list[CursorTheme] = []
        try:
            for entry in base.iterdir():
                if not entry.is_dir():
                    continue
                cursors_dir = entry / "cursors"
                if not cursors_dir.is_dir():
                    continue
                if not self._has_cursor_files(cursors_dir):
                    continue
                name = self._read_theme_name(entry)
                theme = CursorTheme(
                    name=name,
                    directory_name=entry.name,
                    path=entry,
                    cursor_path=cursors_dir,
                    source_type=source,
                    existing_sizes=(),
                    inspected_files=0,
                    failed_inspections=0,
                )
                results.append(theme)
        except PermissionError as exc:
            log.warning("cannot read %s: %s", base, exc)
        return results

    def _has_cursor_files(self, cursors_dir: Path) -> bool:
        try:
            return any(
                f.is_file() and not f.name.startswith(".")
                for f in cursors_dir.iterdir()
            )
        except PermissionError:
            return False

    def _read_theme_name(self, theme_dir: Path) -> str:
        for filename in ("index.theme", "cursor.theme"):
            candidate = theme_dir / filename
            if candidate.is_file():
                name = self._parse_theme_name(candidate)
                if name:
                    return name
        return theme_dir.name

    def _parse_theme_name(self, theme_file: Path) -> str | None:
        parser = configparser.RawConfigParser()
        try:
            parser.read(theme_file, encoding="utf-8")
            for section in ("Icon Theme", "Cursor Theme"):
                if parser.has_section(section):
                    name = parser.get(section, "Name", fallback=None)
                    if name and name.strip():
                        return name.strip()
        except Exception as exc:
            log.debug("failed to parse %s: %s", theme_file, exc)
        return None
