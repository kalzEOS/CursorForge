p# CursorForge

Add additional sizes to installed Xcursor themes on Linux.

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- `xcur2png`
- `xcursorgen`
- ImageMagick (`magick`)

On Arch / CachyOS:
```
sudo pacman -S xcur2png xorg-xcursorgen imagemagick
```

## Quick start

```bash
uv sync
uv run cursorforge
```

## Development

```bash
uv run pytest          # run tests
uv run ruff check .    # lint
uv run mypy src        # type check
```

## Status

**Phase 1** — theme detection, size inspection, and dependency checking are implemented.
Building (Phase 2+) is not yet available.