from __future__ import annotations

import logging
import shutil
import subprocess

from cursorforge.models import DependencyStatus

log = logging.getLogger(__name__)

_DEPS: list[str] = ["xcur2png", "xcursorgen", "magick"]


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
    for name in _DEPS:
        path = shutil.which(name)
        available = path is not None
        version = _get_version(name) if available else None
        log.info("dependency %s: available=%s path=%s version=%s", name, available, path, version)
        results.append(DependencyStatus(
            name=name,
            available=available,
            version=version,
            path=path,
            suggested_package=name,  # actual package name resolved per-distro in distro.py
        ))
    return results


def all_available(statuses: list[DependencyStatus]) -> bool:
    return all(s.available for s in statuses)


def missing_names(statuses: list[DependencyStatus]) -> list[str]:
    return [s.name for s in statuses if not s.available]
