from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cursorforge.models import CursorTheme
from cursorforge.paths import OUTPUT_BASE
from cursorforge.ui.size_panel import SizePanel
from cursorforge.ui.theme_panel import ThemePanel

log = logging.getLogger(__name__)


class _QTextEditHandler(logging.Handler):
    def __init__(self, widget: QPlainTextEdit) -> None:
        super().__init__()
        self._widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self._widget.appendPlainText(msg)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CursorForge")
        self.setMinimumSize(700, 600)
        self._current_theme: CursorTheme | None = None
        self._build_ui()
        self._setup_logging()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)

        # --- Theme panel ---
        self._theme_panel = ThemePanel()
        self._theme_panel.theme_ready.connect(self._on_theme_ready)
        root.addWidget(self._theme_panel)

        # --- Size panel ---
        self._size_panel = SizePanel()
        self._size_panel.selection_changed.connect(self._refresh_output_preview)
        root.addWidget(self._size_panel)

        # --- Output section ---
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Output theme name")
        self._name_edit.textChanged.connect(self._refresh_output_preview)
        output_layout.addWidget(self._name_edit)

        self._preview_label = QLabel()
        self._preview_label.setStyleSheet("color: gray;")
        output_layout.addWidget(self._preview_label)

        self._build_btn = QPushButton("Build Theme")
        self._build_btn.setEnabled(False)
        self._build_btn.setToolTip("Theme building will be available in Phase 2.")
        self._build_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        output_layout.addWidget(self._build_btn)

        root.addWidget(output_group)

        # --- Log section ---
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(2000)
        self._log_view.setMinimumHeight(120)
        log_layout.addWidget(self._log_view)

        root.addWidget(log_group)

    def _setup_logging(self) -> None:
        handler = _QTextEditHandler(self._log_view)
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        handler.setLevel(logging.DEBUG)
        root_log = logging.getLogger()
        root_log.addHandler(handler)
        root_log.setLevel(logging.DEBUG)

    def _on_theme_ready(self, theme: CursorTheme, warning: str | None) -> None:
        self._current_theme = theme
        default_name = f"{theme.directory_name}-Multi"
        self._name_edit.setText(default_name)
        self._size_panel.set_existing_sizes(theme.existing_sizes)
        self._refresh_output_preview()

    def _refresh_output_preview(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._preview_label.setText("Enter an output theme name above.")
            return

        if "/" in name or "\\" in name:
            self._preview_label.setText(
                "<font color='red'>Name must not contain path separators.</font>"
            )
            self._preview_label.setTextFormat(
                Qt.TextFormat.RichText
            )
            return

        dest = OUTPUT_BASE / name
        new_sizes = self._size_panel.new_sizes()
        sizes_str = ", ".join(str(s) for s in new_sizes) if new_sizes else "none"
        self._preview_label.setText(
            f"Destination: {dest}\n"
            f"Sizes to generate: {sizes_str}"
        )
