# CursorForge

CursorForge is a Linux desktop application that adds extra sizes to existing
installed Xcursor themes. It reads a theme already on your system, generates
the missing sizes using ImageMagick, and compiles a new Xcursor theme that
contains both the original sizes and the newly generated ones.

The result is a separate output theme installed alongside the original.
The source theme is never modified.


## What it does

1. Scans your system for installed cursor themes (user and system locations).
2. Inspects each theme to find what sizes are already embedded.
3. Lets you choose which additional sizes to generate.
4. Scales the closest existing cursor images to each new size using Lanczos
   resampling via ImageMagick.
5. Recompiles each cursor file to include all original sizes plus the new ones.
6. Installs the finished theme to the location you choose.

Hotspot coordinates are proportionally scaled so cursors remain accurate after
resizing.


## Requirements

### Runtime dependencies

- Python 3.12 or newer
- PySide6 6.6 or newer (installed automatically by uv)
- `xcur2png` -- extracts Xcursor files into PNG frames
- `xcursorgen` -- compiles PNG frames back into Xcursor files
- ImageMagick (`magick` command) -- scales PNG images

### Installing the external tools

**Arch Linux / CachyOS / Manjaro**

```
sudo pacman -S xcur2png xorg-xcursorgen imagemagick
```

**Fedora**

```
sudo dnf install xcur2png xorg-x11-apps ImageMagick
```

**openSUSE**

```
sudo zypper install xcur2png xcursorgen ImageMagick
```

**Gentoo**

```
sudo emerge x11-misc/xcur2png x11-apps/xcursorgen media-gfx/imagemagick
```

**Debian / Ubuntu / Linux Mint / Pop!_OS**

`xcursorgen` and ImageMagick are available in the standard repositories:

```
sudo apt install x11-apps imagemagick
```

`xcur2png` is not packaged for Debian-based distributions. You need to build
it from source:

```
git clone https://github.com/wwmm/xcur2png
cd xcur2png
make
sudo make install
```

**Other distributions**

Install `xcursorgen`, `xcur2png`, and ImageMagick using your distribution's
package manager. CursorForge will detect missing tools at startup and show
the appropriate instructions for your system.


## Installation

### Step 1 -- install uv

CursorForge uses [uv](https://github.com/astral-sh/uv) for dependency
management. Install it if you do not have it already:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal or run `source ~/.local/bin/env` after installing.

### Step 2 -- clone the repository

```
git clone https://github.com/kalzEOS/CursorForge
cd CursorForge
```

### Step 3 -- install the app

Install CursorForge as a user command so you can launch it from anywhere:

```
uv tool install .
```

This installs the `cursorforge` command to `~/.local/bin/`. Make sure that
directory is in your PATH. On most distributions it already is. If not, add
this line to your shell profile (`~/.bashrc`, `~/.zshrc`, `~/.config/fish/config.fish`, etc.):

```
export PATH="$HOME/.local/bin:$PATH"
```

To uninstall later:

```
uv tool uninstall cursorforge
```

### Step 4 -- add to the application menu

Run these commands from inside the cloned CursorForge folder to install the
icon and register the app with your desktop environment:

```
mkdir -p ~/.local/share/icons/hicolor/scalable/apps
cp assets/cursorforge.svg ~/.local/share/icons/hicolor/scalable/apps/cursorforge.svg

mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/cursorforge.desktop << 'EOF'
[Desktop Entry]
Name=CursorForge
Comment=Add extra sizes to Xcursor themes
Exec=cursorforge
Icon=cursorforge
Type=Application
Categories=Settings;
EOF
```

After running these commands, CursorForge will appear in your application
menu and can be pinned to a panel or dock like any other app.


## Uninstalling

```
uv tool uninstall cursorforge
rm ~/.local/share/applications/cursorforge.desktop
rm ~/.local/share/icons/hicolor/scalable/apps/cursorforge.svg
```


## Running

Once installed:

```
cursorforge
```

Or without installing, directly from the cloned folder:

```
uv run cursorforge
```


## Usage

1. Select a cursor theme from the dropdown at the top. CursorForge lists all
   themes found in `~/.icons`, `~/.local/share/icons`, and `/usr/share/icons`.

2. The app inspects the theme and shows which sizes are already present.
   Those sizes appear checked and grayed out in the Target Sizes grid.

3. Check the sizes you want to add. You can also type custom sizes in the
   field at the bottom of the grid (for example: 18, 26, 100) and press Add.

4. Enter a name for the output theme and choose where to install it:
   - User -- installs to `~/.local/share/icons` (no root required)
   - System -- installs to `/usr/share/icons` (requires root via pkexec)
   - Custom directory -- choose any folder

5. Click Build Theme. A progress window shows each cursor being processed.
   When the build is complete the window displays the output location and
   a summary of what was generated.

6. Switch to the new theme in your desktop environment's cursor settings.

The log panel at the bottom of the main window can be expanded to see
detailed output. Use Export Log to save it as a text file if you need to
report an issue.


## Notes

- The source theme is never modified. CursorForge always writes a new,
  separate theme.
- Animated cursors are fully supported. Each frame is scaled independently
  and the delay values are preserved.
- Symlinks inside a cursor theme (used to point alternate cursor names to
  the same file) are preserved in the output theme.
- If a cursor in the source theme already contains a size you selected,
  that size is carried forward from the original rather than re-scaled.


## Development

Run the test suite:

```
uv run pytest
```

Lint:

```
uv run ruff check .
```

Type check:

```
uv run mypy src
```


## License

CursorForge is released under the GNU General Public License v3.0 or later.
See the LICENSE file for details.
