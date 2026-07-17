#!/usr/bin/env bash
# Build CursorForge packages. Run from the repo root.
# Requires: nfpm        → https://nfpm.goreleaser.com
#           appimage-builder → pip install appimage-builder  (AppImage only)
# Usage: ./packaging/build-packages.sh [deb|rpm|arch|appimage|all]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG_DIR="$ROOT/packaging"
DIST="$ROOT/dist/packages"
mkdir -p "$DIST"

clean_pycache() {
    find "$ROOT/src" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$ROOT/src" -name "*.pyc" -o -name "*.pyo" | xargs rm -f 2>/dev/null || true
}

build_deb() {
    echo "==> Building .deb"
    clean_pycache
    (cd "$PKG_DIR" && nfpm package --config nfpm-deb.yaml --packager deb --target "$DIST")
    echo "==> .deb written to $DIST"
}

build_rpm() {
    echo "==> Building .rpm  (targets Fedora 40+ / Python 3.12)"
    clean_pycache
    (cd "$PKG_DIR" && nfpm package --config nfpm-rpm.yaml --packager rpm --target "$DIST")
    echo "==> .rpm written to $DIST"
}

build_arch() {
    echo "==> Building Arch package"
    PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    export PYVER
    clean_pycache
    # nfpm doesn't expand env vars in dst paths, so we preprocess with envsubst
    envsubst < "$PKG_DIR/nfpm-arch.yaml" > /tmp/nfpm-arch-resolved.yaml
    (cd "$PKG_DIR" && nfpm package --config /tmp/nfpm-arch-resolved.yaml --packager archlinux --target "$DIST")
    rm -f /tmp/nfpm-arch-resolved.yaml
    echo "==> Arch package written to $DIST"
}

build_appimage() {
    echo "==> Building AppImage"
    if ! command -v appimage-builder &>/dev/null; then
        echo "appimage-builder not found. Install it with: pip install appimage-builder"
        exit 1
    fi
    # Read version from __init__.py as the single source of truth
    VERSION="$(python3 -c "import sys; sys.path.insert(0,'$ROOT/src'); from cursorforge import __version__; print(__version__)")"
    mkdir -p "$DIST"
    APPIMAGE_RECIPE_TMP="$PKG_DIR/appimage/AppImageBuilder.$$.yml"
    trap 'rm -f "$APPIMAGE_RECIPE_TMP"' EXIT
    export VERSION
    envsubst < "$PKG_DIR/appimage/AppImageBuilder.yml" > "$APPIMAGE_RECIPE_TMP"
    # Run from packaging/appimage/ so relative paths in the recipe resolve correctly
    (cd "$PKG_DIR/appimage" && appimage-builder --recipe "$(basename "$APPIMAGE_RECIPE_TMP")")
    mv "$PKG_DIR/appimage"/CursorForge-*.AppImage "$DIST/" 2>/dev/null || true
    rm -rf "$PKG_DIR/appimage/AppDir"
    rm -f "$APPIMAGE_RECIPE_TMP"
    trap - EXIT
    echo "==> AppImage written to $DIST"
}

TARGET="${1:-all}"

case "$TARGET" in
    deb)      build_deb ;;
    rpm)      build_rpm ;;
    arch)     build_arch ;;
    appimage) build_appimage ;;
    all)
        build_deb
        build_rpm
        build_arch
        build_appimage
        ;;
    *)
        echo "Usage: $0 [deb|rpm|arch|appimage|all]"
        exit 1
        ;;
esac

echo ""
echo "Packages in $DIST:"
ls -lh "$DIST"/*.{deb,rpm,zst,AppImage} 2>/dev/null || true
