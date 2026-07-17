from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
import sys
from typing import cast

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from cursorforge.builder import BuildResult, ThemeBuilder
from cursorforge.models import CursorTheme
from cursorforge.paths import SYSTEM_OUTPUT_BASE, USER_OUTPUT_BASE
from cursorforge.root_build import build_privileged_command, parse_output_line
from cursorforge.ui.progress_dialog import BuildProgressDialog
from cursorforge.ui.size_panel import SizePanel
from cursorforge.ui.theme_panel import ThemePanel

log = logging.getLogger(__name__)


class _LogRelay(QObject):
    message = Signal(str)


class _ThreadSafeLogHandler(logging.Handler):
    def __init__(self, widget: QPlainTextEdit) -> None:
        super().__init__()
        self._relay = _LogRelay()
        self._relay.message.connect(widget.appendPlainText)

    def emit(self, record: logging.LogRecord) -> None:
        self._relay.message.emit(self.format(record))


class _BuildSignals(QObject):
    progress = Signal(str, int, int)
    finished = Signal(object)  # BuildResult


class _BuildWorker(QRunnable):
    def __init__(
        self,
        theme: CursorTheme,
        new_sizes: list[int],
        output_path: Path,
    ) -> None:
        super().__init__()
        self._theme = theme
        self._new_sizes = new_sizes
        self._output_path = output_path
        self.signals = _BuildSignals()

    def run(self) -> None:
        def on_progress(msg: str, current: int, total: int) -> None:
            self.signals.progress.emit(msg, current, total)

        try:
            builder = ThemeBuilder()
            result = builder.build(
                self._theme,
                self._new_sizes,
                self._output_path,
                on_progress=on_progress,
            )
        except Exception as exc:
            log.exception("build worker crashed")
            result = BuildResult(
                success=False,
                output_path=self._output_path,
                errors=[str(exc)],
            )
        self.signals.finished.emit(result)


class _PrivilegedBuildWorker(QRunnable):
    def __init__(
        self,
        theme: CursorTheme,
        new_sizes: list[int],
        output_path: Path,
    ) -> None:
        super().__init__()
        self._theme = theme
        self._new_sizes = new_sizes
        self._output_path = output_path
        self.signals = _BuildSignals()

    def run(self) -> None:
        tmp_pkg_dir = Path(tempfile.mkdtemp(prefix="cursorforge_root_"))
        process = None
        result: BuildResult | None = None
        output_lines: list[str] = []
        returncode = 1
        # pkexec strips environment variables, so PYTHONPATH is never inherited
        # by the privileged helper. To ensure cursorforge is importable as root
        # (whether we're running from an AppImage, from source, or installed),
        # copy the package to a plain /tmp directory that root can read and pass
        # PYTHONPATH explicitly via `pkexec env PYTHONPATH=...`.
        import cursorforge as _cf
        shutil.copytree(str(Path(_cf.__file__).parent), str(tmp_pkg_dir / "cursorforge"))

        python_exe = shutil.which("python3") or "python3"
        try:
            command = build_privileged_command(
                python_exe,
                self._theme.cursor_path,
                self._theme.directory_name,
                self._output_path,
                self._new_sizes,
                pythonpath=str(tmp_pkg_dir),
            )
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.rstrip("\n")
                parsed = parse_output_line(line)
                if parsed is None:
                    if line.strip():
                        output_lines.append(line.strip())
                        log.debug("pkexec helper: %s", line)
                    continue

                kind, payload = parsed
                if kind == "progress":
                    message, current, total = cast(tuple[str, int, int], payload)
                    self.signals.progress.emit(message, current, total)
                elif kind == "result":
                    result = cast(BuildResult, payload)

            returncode = process.wait()
        except FileNotFoundError as exc:
            log.exception("privileged build helper could not start")
            result = BuildResult(
                success=False,
                output_path=self._output_path,
                errors=[str(exc)],
            )
        except Exception as exc:  # pragma: no cover - defensive catch for privileged path
            log.exception("privileged build helper crashed")
            result = BuildResult(
                success=False,
                output_path=self._output_path,
                errors=[str(exc)],
            )
        finally:
            shutil.rmtree(tmp_pkg_dir, ignore_errors=True)

        if result is None:
            errors = output_lines[-3:] if output_lines else []
            if not errors:
                errors = [f"pkexec build exited with status {returncode}."]
            result = BuildResult(
                success=False,
                output_path=self._output_path,
                errors=errors,
            )
        elif returncode != 0 and result.success:
            result = BuildResult(
                success=False,
                output_path=result.output_path,
                sizes_added=result.sizes_added,
                cursors_processed=result.cursors_processed,
                cursors_failed=result.cursors_failed,
                errors=result.errors or [f"pkexec build exited with status {returncode}."],
            )

        self.signals.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CursorForge")
        self.setMinimumWidth(700)
        self.resize(700, 820)
        self._current_theme: CursorTheme | None = None
        self._custom_dest: Path | None = None
        self._progress_dialog: BuildProgressDialog | None = None
        self._height_locked = False
        self._pre_log_height: int = 0
        self._build_ui()
        self._setup_logging()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._height_locked:
            self._height_locked = True
            # Lock minimum height to exactly what the laid-out content needs,
            # so the window can never be resized small enough to squish anything.
            self.setMinimumHeight(self.sizeHint().height())

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)

        # --- Theme panel ---
        self._theme_panel = ThemePanel()
        self._theme_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._theme_panel.theme_ready.connect(self._on_theme_ready)
        root.addWidget(self._theme_panel)

        # --- Size panel ---
        self._size_panel = SizePanel()
        self._size_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._size_panel.selection_changed.connect(self._refresh_build_state)
        root.addWidget(self._size_panel)

        # --- Output section ---
        output_group = QGroupBox("Output")
        output_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        output_layout = QVBoxLayout(output_group)

        # Theme name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Theme name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. MyTheme-Multi")
        self._name_edit.textChanged.connect(self._refresh_build_state)
        name_row.addWidget(self._name_edit)
        output_layout.addLayout(name_row)

        # Install location — stacked vertically so they never truncate
        output_layout.addWidget(QLabel("Install to:"))

        self._loc_user = QRadioButton("User (~/.local/share/icons)")
        self._loc_system = QRadioButton("System (/usr/share/icons) — requires root")
        self._loc_custom = QRadioButton("Choose Directory")
        self._loc_user.setChecked(True)

        self._loc_group = QButtonGroup(self)
        self._loc_group.addButton(self._loc_user)
        self._loc_group.addButton(self._loc_system)
        self._loc_group.addButton(self._loc_custom)
        self._loc_group.buttonClicked.connect(self._on_location_changed)

        indent = QWidget()
        indent_layout = QVBoxLayout(indent)
        indent_layout.setContentsMargins(16, 4, 0, 4)
        indent_layout.setSpacing(4)
        indent_layout.addWidget(self._loc_user)
        indent_layout.addWidget(self._loc_system)
        indent_layout.addWidget(self._loc_custom)
        output_layout.addWidget(indent)

        # Custom directory picker (shown only when "Choose Directory" is selected)
        self._custom_dir_row = QWidget()
        custom_dir_layout = QHBoxLayout(self._custom_dir_row)
        custom_dir_layout.setContentsMargins(16, 0, 0, 0)
        self._custom_dir_edit = QLineEdit()
        self._custom_dir_edit.setReadOnly(True)
        self._custom_dir_edit.setPlaceholderText("No directory selected")
        self._browse_btn = QPushButton("Browse")
        self._browse_btn.clicked.connect(self._browse_directory)
        custom_dir_layout.addWidget(self._custom_dir_edit)
        custom_dir_layout.addWidget(self._browse_btn)
        self._custom_dir_row.hide()
        # Retain layout space when hidden so the section height never shifts.
        sp_cdr = self._custom_dir_row.sizePolicy()
        sp_cdr.setRetainSizeWhenHidden(True)
        self._custom_dir_row.setSizePolicy(sp_cdr)
        output_layout.addWidget(self._custom_dir_row)

        # System install warning
        self._system_warning = QLabel(
            "Warning: installing to /usr/share/icons requires root privileges. "
            "CursorForge will use pkexec to request elevation at build time."
        )
        self._system_warning.setWordWrap(True)
        self._system_warning.setStyleSheet("color: orange;")
        self._system_warning.hide()
        sp_warn = self._system_warning.sizePolicy()
        sp_warn.setRetainSizeWhenHidden(True)
        self._system_warning.setSizePolicy(sp_warn)
        output_layout.addWidget(self._system_warning)

        # Destination preview
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("color: gray;")
        output_layout.addWidget(self._preview_label)

        # Build button
        self._build_btn = QPushButton("Build Theme")
        self._build_btn.setEnabled(False)
        self._build_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._build_btn.clicked.connect(self._on_build_clicked)
        output_layout.addWidget(self._build_btn)

        root.addWidget(output_group)

        # --- Log section ---
        log_header = QHBoxLayout()

        self._log_toggle = QPushButton("▶  Show Log")
        self._log_toggle.setFlat(True)
        self._log_toggle.setStyleSheet("font-weight: bold; text-align: left;")
        self._log_toggle.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._log_toggle.clicked.connect(self._toggle_log)
        log_header.addWidget(self._log_toggle)

        self._export_btn = QPushButton("Export Log")
        self._export_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._export_btn.clicked.connect(self._export_log)
        self._export_btn.hide()
        log_header.addWidget(self._export_btn)
        log_header.addStretch()
        root.addLayout(log_header)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(2000)
        self._log_view.setMinimumHeight(110)
        self._log_view.setMaximumHeight(260)
        self._log_view.hide()
        root.addWidget(self._log_view)

    def _setup_logging(self) -> None:
        handler = _ThreadSafeLogHandler(self._log_view)
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        handler.setLevel(logging.DEBUG)
        root_log = logging.getLogger()
        root_log.addHandler(handler)
        root_log.setLevel(logging.DEBUG)

    def _on_theme_ready(self, theme: CursorTheme, _warning: str | None) -> None:
        self._current_theme = theme
        self._name_edit.setText(f"{theme.directory_name}-Multi")
        self._size_panel.set_existing_sizes(theme.existing_sizes)
        self._refresh_build_state()

    def _on_location_changed(self) -> None:
        self._system_warning.setVisible(self._loc_system.isChecked())
        self._custom_dir_row.setVisible(self._loc_custom.isChecked())
        if self._loc_custom.isChecked() and not self._custom_dest:
            self._browse_directory()
        self._refresh_build_state()

    def _browse_directory(self) -> None:
        start = str(self._custom_dest or Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Choose Destination Directory", start)
        if chosen:
            self._custom_dest = Path(chosen)
            self._custom_dir_edit.setText(chosen)
        self._refresh_build_state()

    def _refresh_build_state(self) -> None:
        name = self._name_edit.text().strip()
        new_sizes = self._size_panel.new_sizes()

        if not name:
            self._preview_label.setText("Enter an output theme name above.")
            self._build_btn.setEnabled(False)
            return

        if "/" in name or "\\" in name:
            self._preview_label.setText(
                "<font color='red'>Theme name must not contain path separators.</font>"
            )
            self._preview_label.setTextFormat(Qt.TextFormat.RichText)
            self._build_btn.setEnabled(False)
            return

        if self._loc_system.isChecked():
            base: Path | None = SYSTEM_OUTPUT_BASE
        elif self._loc_custom.isChecked():
            base = self._custom_dest
        else:
            base = USER_OUTPUT_BASE

        if base is None:
            self._preview_label.setText("Select a destination directory above.")
            self._build_btn.setEnabled(False)
            return

        dest = base / name
        sizes_str = ", ".join(str(s) for s in new_sizes) if new_sizes else "none selected"
        self._preview_label.setText(
            f"Destination: {dest}\n"
            f"Sizes to generate: {sizes_str}"
        )

        ready = (
            self._current_theme is not None
            and bool(new_sizes)
            and bool(name)
        )
        self._build_btn.setEnabled(ready)

    def _on_build_clicked(self) -> None:
        theme = self._current_theme
        if theme is None:
            return

        dest = self.output_destination()
        if dest is None:
            QMessageBox.warning(self, "Build Error", "No valid output destination selected.")
            return

        new_sizes = self._size_panel.new_sizes()
        if not new_sizes:
            QMessageBox.warning(self, "Build Error", "No new sizes selected.")
            return

        if dest.exists():
            reply = QMessageBox.question(
                self,
                "Destination Exists",
                f"{dest} already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        log.info(
            "Starting build: %s → %s (new sizes: %s)",
            theme.directory_name,
            dest,
            new_sizes,
        )

        self._build_btn.setEnabled(False)
        dialog = BuildProgressDialog(
            theme_name=theme.directory_name,
            new_sizes=new_sizes,
            parent=self,
        )
        self._progress_dialog = dialog

        if self._loc_system.isChecked():
            if shutil.which("pkexec") is None:
                QMessageBox.critical(
                    self,
                    "Build Error",
                    "pkexec is required to request administrator authorization for system installs.",
                )
                self._build_btn.setEnabled(True)
                self._progress_dialog = None
                return
            dialog.update_progress("Requesting administrator authorization…", 0, 100)
            worker = _PrivilegedBuildWorker(theme, new_sizes, dest)
        else:
            worker = _BuildWorker(theme, new_sizes, dest)
        worker.signals.progress.connect(dialog.update_progress)
        worker.signals.finished.connect(self._on_build_finished)
        QThreadPool.globalInstance().start(worker)

        # open() is non-blocking: shows the dialog modally without freezing
        # the main event loop, so worker signals are delivered normally.
        dialog.open()

    def _on_build_finished(self, result: BuildResult) -> None:
        self._build_btn.setEnabled(True)
        if self._progress_dialog is not None:
            self._progress_dialog.show_result(result)
            self._progress_dialog = None
        if result.success:
            log.info("Build complete: %s", result.output_path)
        else:
            log.error("Build failed: %s", result.errors)

    def _toggle_log(self) -> None:
        visible = self._log_view.isVisible()
        if not visible:
            # Record height now so we can restore it exactly when hiding
            self._pre_log_height = self.height()
            self._log_view.setVisible(True)
            self._export_btn.setVisible(True)
            self._log_toggle.setText("▼  Log")
            self.adjustSize()
        else:
            self._log_view.setVisible(False)
            self._export_btn.setVisible(False)
            self._log_toggle.setText("▶  Show Log")
            # Restore the exact height from before the log was shown
            restore = self._pre_log_height if self._pre_log_height else self.minimumHeight()
            self.resize(self.width(), max(self.minimumHeight(), restore))

    def _export_log(self) -> None:
        default_name = f"cursorforge-log-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            str(Path.home() / default_name),
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        try:
            Path(path).write_text(self._log_view.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def output_name(self) -> str:
        return self._name_edit.text().strip()

    def output_destination(self) -> Path | None:
        name = self.output_name()
        if not name:
            return None
        if self._loc_system.isChecked():
            return SYSTEM_OUTPUT_BASE / name
        if self._loc_custom.isChecked():
            return (self._custom_dest / name) if self._custom_dest else None
        return USER_OUTPUT_BASE / name
