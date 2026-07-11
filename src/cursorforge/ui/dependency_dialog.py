from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cursorforge.dependencies import missing_names
from cursorforge.distro import InstallInfo, detect_distro, get_install_info
from cursorforge.models import DependencyStatus


class DependencyDialog(QDialog):
    def __init__(self, statuses: list[DependencyStatus], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Missing Dependencies")
        self.setMinimumWidth(520)

        distro = detect_distro()
        missing = missing_names(statuses)
        install_info = get_install_info(missing, distro) if missing else None

        self._build_ui(statuses, distro.pretty_name, install_info)

    def _build_ui(
        self,
        statuses: list[DependencyStatus],
        distro_name: str,
        install_info: InstallInfo | None,
    ) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(
            f"<b>CursorForge</b> requires external programs to process cursor files. "
            f"Some are missing on <i>{distro_name}</i>."
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setWordWrap(True)
        layout.addWidget(header)

        layout.addSpacing(6)

        # per-dependency status rows
        for s in statuses:
            row = QHBoxLayout()
            icon_label = QLabel()
            style = self.style()
            assert style is not None
            if s.available:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
                text = f"<b>{s.name}</b> &nbsp; <font color='green'>found</font>"
                if s.version:
                    text += f" &nbsp;<font color='gray'>({s.version})</font>"
            else:
                icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
                text = f"<b>{s.name}</b> &nbsp; <font color='red'>not found</font>"
            icon_label.setPixmap(icon.pixmap(16, 16))
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(icon_label)
            row.addWidget(lbl, stretch=1)
            layout.addLayout(row)

        if install_info is None:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
            buttons.accepted.connect(self.accept)
            layout.addWidget(buttons)
            return

        layout.addSpacing(8)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # install command section
        if install_info.command:
            layout.addWidget(QLabel(f"<b>Install command ({install_info.distro.pretty_name}):</b>"))
            cmd_box = QTextEdit()
            cmd_box.setPlainText(install_info.command)
            cmd_box.setReadOnly(True)
            cmd_box.setFixedHeight(48)
            layout.addWidget(cmd_box)

            copy_btn = QPushButton("Copy Command")
            copy_btn.clicked.connect(lambda: self._copy(install_info.command or ""))
            layout.addWidget(copy_btn)
        else:
            layout.addWidget(QLabel(
                "<font color='orange'><b>Could not determine an install command for your distribution.</b></font>"
            ))

        # per-package notes for packages not in repos
        if install_info.unavailable_notes:
            layout.addSpacing(6)
            for note in install_info.unavailable_notes:
                note_label = QLabel(f"<b>Note:</b> {note}")
                note_label.setWordWrap(True)
                note_label.setTextFormat(Qt.TextFormat.RichText)
                layout.addWidget(note_label)

        layout.addSpacing(4)
        layout.addWidget(QLabel(
            "<font color='gray'>You can continue without all dependencies, "
            "but theme building will fail until they are installed.</font>"
        ))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _copy(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
