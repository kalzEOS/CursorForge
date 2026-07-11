from pathlib import Path

from cursorforge.models import ThemeSource

USER_ICONS = Path.home() / ".icons"
USER_LOCAL_SHARE_ICONS = Path.home() / ".local" / "share" / "icons"
SYSTEM_ICONS = Path("/usr/share/icons")
LOG_DIR = Path.home() / ".local" / "state" / "cursorforge"

USER_OUTPUT_BASE = Path.home() / ".local" / "share" / "icons"
SYSTEM_OUTPUT_BASE = Path("/usr/share/icons")

SEARCH_PATHS: list[tuple[Path, ThemeSource]] = [
    (USER_ICONS, ThemeSource.USER_ICONS),
    (USER_LOCAL_SHARE_ICONS, ThemeSource.USER_LOCAL_SHARE),
    (SYSTEM_ICONS, ThemeSource.SYSTEM),
]
