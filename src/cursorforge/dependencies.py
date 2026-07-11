from __future__ import annotations

import logging
import shutil
import subprocess

from cursorforge.models import DependencyStatus

log = logging.getLogger(__name__)

_DEPS: list[tuple[str, str]] = [
    ("xcur2png", "xcur2png"),
    ("xcursorgen", "xorg-xcursorgen"),
    ("magick", "imagemagick"),
]

PACMAN_COMMAND = "sudo pacman -S xcur2png xorg-xcursorgen imagemagick"


def _get_version(name: str) -> str | None:
    try:
        result = subprocess.run(
            [name, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        line = (result.stdout or result.stderr or "").splitlines()
        return line[0].strip() if line else None
    except Exception:
        return None


def check_dependencies() -> list[DependencyStatus]:
    results: list[DependencyStatus] = []
    for name, pkg in _DEPS:
        path = shutil.which(name)
        available = path is not None
        version = _get_version(name) if available else None
        log.info("dependency %s: available=%s path=%s version=%s", name, available, path, version)
        results.append(DependencyStatus(
            name=name,
            available=available,
            version=version,
            path=path,
            suggested_package=pkg,
        ))
    return results


def all_available(statuses: list[DependencyStatus]) -> bool:
    return all(s.available for s in statuses)
