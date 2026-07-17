from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ThemeSource(Enum):
    USER_ICONS = "~/.icons"
    USER_LOCAL_SHARE = "~/.local/share/icons"
    SYSTEM = "/usr/share/icons"

    def label(self) -> str:
        labels = {
            ThemeSource.USER_ICONS: "User install",
            ThemeSource.USER_LOCAL_SHARE: "User install",
            ThemeSource.SYSTEM: "System install",
        }
        return labels[self]


@dataclass(frozen=True)
class CursorTheme:
    name: str
    directory_name: str
    path: Path
    cursor_path: Path
    source_type: ThemeSource
    existing_sizes: tuple[int, ...]
    inspected_files: int
    failed_inspections: int

    def display_label(self) -> str:
        return f"{self.name} — {self.source_type.value}"

    def has_inconsistent_sizes(self) -> bool:
        return False  # set by ThemeScanner when sizes differ across cursors


@dataclass(frozen=True)
class CursorThemeWithWarning:
    theme: CursorTheme
    size_inconsistency_warning: str | None


@dataclass(frozen=True)
class CursorFrame:
    size: int
    xhot: int
    yhot: int
    image_path: Path
    delay_ms: int
    source_order: int


@dataclass
class ExtractedCursor:
    original_path: Path
    frames: list[CursorFrame] = field(default_factory=list)


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    version: str | None
    path: str | None
    suggested_package: str
