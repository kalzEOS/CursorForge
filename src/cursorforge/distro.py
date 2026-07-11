from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# (dep_binary, arch_pkg, debian_pkg, fedora_pkg, opensuse_pkg, gentoo_pkg)
# None means "not in standard repos for that distro"
_PACKAGE_TABLE: dict[str, dict[str, str | None]] = {
    "xcur2png": {
        "arch":    "xcur2png",
        "debian":  None,           # not in standard repos
        "fedora":  "xcur2png",     # available in some Fedora versions
        "opensuse": "xcur2png",
        "gentoo":  "x11-misc/xcur2png",
    },
    "xcursorgen": {
        "arch":    "xorg-xcursorgen",
        "debian":  "x11-apps",
        "fedora":  "xorg-x11-apps",
        "opensuse": "xcursorgen",
        "gentoo":  "x11-apps/xcursorgen",
    },
    "magick": {
        "arch":    "imagemagick",
        "debian":  "imagemagick",
        "fedora":  "ImageMagick",
        "opensuse": "ImageMagick",
        "gentoo":  "media-gfx/imagemagick",
    },
}

_PACKAGE_MANAGERS: dict[str, str] = {
    "arch":    "sudo pacman -S",
    "debian":  "sudo apt install",
    "fedora":  "sudo dnf install",
    "opensuse": "sudo zypper install",
    "gentoo":  "sudo emerge",
}

# Packages that are NOT reliably available and need an extra note
_UNAVAILABLE_NOTES: dict[str, dict[str, str]] = {
    "xcur2png": {
        "debian": (
            "xcur2png is not in the standard Debian/Ubuntu repositories. "
            "You can build it from source:\n"
            "  git clone https://github.com/wwmm/xcur2png && cd xcur2png\n"
            "  make && sudo make install"
        ),
    },
}


@dataclass(frozen=True)
class DistroInfo:
    id: str        # e.g. "cachyos", "ubuntu", "fedora"
    id_like: str   # normalized family: "arch", "debian", "fedora", "opensuse", "gentoo", "unknown"
    pretty_name: str


@dataclass
class InstallInfo:
    command: str | None          # full install command, None if can't determine
    unavailable_notes: list[str] # messages for packages with no repo equivalent
    distro: DistroInfo


def detect_distro() -> DistroInfo:
    os_release = Path("/etc/os-release")
    if not os_release.is_file():
        return DistroInfo(id="unknown", id_like="unknown", pretty_name="Unknown Linux")

    data: dict[str, str] = {}
    try:
        for line in os_release.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" not in line or line.startswith("#"):
                continue
            key, _, val = line.partition("=")
            data[key.strip()] = val.strip().strip('"')
    except OSError as exc:
        log.warning("cannot read /etc/os-release: %s", exc)
        return DistroInfo(id="unknown", id_like="unknown", pretty_name="Unknown Linux")

    distro_id = data.get("ID", "unknown").lower()
    id_like_raw = data.get("ID_LIKE", "").lower()
    pretty_name = data.get("PRETTY_NAME", distro_id)

    family = _resolve_family(distro_id, id_like_raw)
    log.info("detected distro: id=%s id_like=%r family=%s", distro_id, id_like_raw, family)
    return DistroInfo(id=distro_id, id_like=family, pretty_name=pretty_name)


def _resolve_family(distro_id: str, id_like: str) -> str:
    candidates = [distro_id] + id_like.split()
    priority = ["arch", "debian", "fedora", "opensuse", "gentoo"]
    for family in priority:
        if any(family in c for c in candidates):
            return family
    # Ubuntu is "debian"-like but might not say so explicitly
    if "ubuntu" in candidates or "mint" in candidates or "pop" in candidates:
        return "debian"
    return "unknown"


def get_install_info(missing_names: list[str], distro: DistroInfo | None = None) -> InstallInfo:
    if distro is None:
        distro = detect_distro()

    family = distro.id_like
    manager = _PACKAGE_MANAGERS.get(family)
    notes: list[str] = []
    packages: list[str] = []

    for dep in missing_names:
        pkg_map = _PACKAGE_TABLE.get(dep, {})
        pkg = pkg_map.get(family)

        if pkg is None:
            # Package not in repos for this distro
            note = _UNAVAILABLE_NOTES.get(dep, {}).get(family)
            if note:
                notes.append(note)
            else:
                notes.append(
                    f"'{dep}' may not be available in your distribution's repositories. "
                    f"Search your package manager or build from source."
                )
        else:
            packages.append(pkg)

    if not packages or manager is None:
        command = None
        if manager is None and family == "unknown":
            notes.insert(
                0,
                f"Could not detect your package manager (distro: {distro.pretty_name}). "
                "Install xcur2png, xcursorgen, and ImageMagick using your system's package manager.",
            )
    else:
        command = f"{manager} {' '.join(packages)}"

    return InstallInfo(command=command, unavailable_notes=notes, distro=distro)
