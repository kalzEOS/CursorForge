from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from cursorforge.models import CursorTheme
from cursorforge.paths import SYSTEM_OUTPUT_BASE, USER_OUTPUT_BASE
from cursorforge.ui.size_panel import SizePanel
from cursorforge.ui.theme_panel import ThemePanel

log = logging.getLogger(__name__)


class _QTextEditHandler(logging.Handler):
    def __init__(self, widget: QPlainTextEdit) -> None:
        super().__init__()
        self._widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        self._widget.appendPlainText(self.format(record))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CursorForge")
        self.setMinimumSize(700, 640)
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

        # Theme name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Theme name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. MyTheme-Multi")
        self._name_edit.textChanged.connect(self._refresh_output_preview)
        name_row.addWidget(self._name_edit)
        output_layout.addLayout(name_row)

        # Install location radio buttons
        location_row = QHBoxLayout()
        location_row.addWidget(QLabel("Install to:"))

        self._loc_user = QRadioButton("User only  (~/.local/share/icons)")
        self._loc_system = QRadioButton("System  (/usr/share/icons)  — requires root")
        self._loc_user.setChecked(True)

        self._loc_group = QButtonGroup(self)
        self._loc_group.addButton(self._loc_user)
        self._loc_group.addButton(self._loc_system)
        self._loc_group.buttonClicked.connect(self._on_location_changed)

        location_row.addWidget(self._loc_user)
        location_row.addWidget(self._loc_system)
        location_row.addStretch()
        output_layout.addLayout(location_row)

        # System install warning
        self._system_warning = QLabel(
            "Warning: installing to /usr/share/icons requires root privileges. "
            "CursorForge will use pkexec to request elevation at build time."
        )
        self._system_warning.setWordWrap(True)
        self._system_warning.setStyleSheet("color: orange;")
        self._system_warning.hide()
        output_layout.addWidget(self._system_warning)

        # Preview
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("color: gray;")
        output_layout.addWidget(self._preview_label)

        # Build button
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
        self._log_view.setMinimumHeight(110)
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
        self._name_edit.setText(f"{theme.directory_name}-Multi")
        self._size_panel.set_existing_sizes(theme.existing_sizes)
        self._refresh_output_preview()

    def _on_location_changed(self) -> None:
        self._system_warning.setVisible(self._loc_system.isChecked())
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
            self._preview_label.setTextFormat(Qt.TextFormat.RichText)
            return

        base = SYSTEM_OUTPUT_BASE if self._loc_system.isChecked() else USER_OUTPUT_BASE
        dest = base / name
        new_sizes = self._size_panel.new_sizes()
        sizes_str = ", ".join(str(s) for s in new_sizes) if new_sizes else "none selected"
        self._preview_label.setText(
            f"Destination: {dest}\n"
            f"Sizes to generate: {sizes_str}"
        )

    def output_name(self) -> str:
        return self._name_edit.text().strip()

    def install_to_system(self) -> bool:
        return self._loc_system.isChecked()
