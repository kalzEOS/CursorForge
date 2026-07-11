from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from cursorforge.dependencies import PACMAN_COMMAND
from cursorforge.models import DependencyStatus


class DependencyDialog(QDialog):
    def __init__(self, statuses: list[DependencyStatus], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Missing Dependencies")
        self.setMinimumWidth(480)
        self._build_ui(statuses)

    def _build_ui(self, statuses: list[DependencyStatus]) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(
            "CursorForge requires the following external programs. "
            "Some are missing:"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        for s in statuses:
            row = QHBoxLayout()
            icon_label = QLabel()
            style = self.style()
            assert style is not None
            if s.available:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
                status_text = f"<b>{s.name}</b> — found ({s.version or 'unknown version'})"
            else:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
                status_text = f"<b>{s.name}</b> — <font color='red'>not found</font>"
            icon_label.setPixmap(icon.pixmap(16, 16))
            row.addWidget(icon_label)
            row.addWidget(QLabel(status_text), stretch=1)
            layout.addLayout(row)

        layout.addSpacing(8)

        missing = [s for s in statuses if not s.available]
        if missing:
            pkg_names = " ".join(s.suggested_package for s in missing)
            install_label = QLabel(
                f"Install missing packages (Arch / CachyOS):\n<code>{PACMAN_COMMAND}</code>"
            )
            install_label.setWordWrap(True)
            install_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(install_label)

            copy_btn = QPushButton("Copy Install Command")
            copy_btn.clicked.connect(self._copy_command)
            layout.addWidget(copy_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _copy_command(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(PACMAN_COMMAND)
