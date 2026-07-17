from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, SignalInstance
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cursorforge.inspector import CursorInspector
from cursorforge.models import CursorTheme
from cursorforge.scanner import ThemeScanner

log = logging.getLogger(__name__)


class _InspectSignals(QObject):
    done = Signal(object)  # CursorTheme (updated with sizes)
    error = Signal(str)


class _InspectWorker(QRunnable):
    def __init__(self, theme: CursorTheme) -> None:
        super().__init__()
        self._theme = theme
        self.signals = _InspectSignals()

    def run(self) -> None:
        try:
            inspector = CursorInspector()
            sizes, warning, inspected, failed = inspector.inspect_theme(self._theme)
            updated = CursorTheme(
                name=self._theme.name,
                directory_name=self._theme.directory_name,
                path=self._theme.path,
                cursor_path=self._theme.cursor_path,
                source_type=self._theme.source_type,
                existing_sizes=sizes,
                inspected_files=inspected,
                failed_inspections=failed,
            )
            # attach warning via a simple wrapper dict for the signal
            self.signals.done.emit((updated, warning))
        except Exception as exc:
            log.exception("inspect worker failed")
            self.signals.error.emit(str(exc))


class ThemePanel(QGroupBox):
    theme_ready = Signal(object, object)  # (CursorTheme, warning: str | None)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Cursor Theme", parent)
        self._themes: list[CursorTheme] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # selector row
        row = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._combo.currentIndexChanged.connect(self._on_index_changed)
        row.addWidget(self._combo)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self._refresh_btn)
        root.addLayout(row)

        # info labels
        self._path_label = QLabel()
        self._path_label.setWordWrap(True)
        self._type_label = QLabel()
        self._sizes_label = QLabel()

        self._warning_label = QLabel()
        self._warning_label.setWordWrap(True)
        self._warning_label.setStyleSheet("color: orange;")
        self._warning_label.hide()

        self._inspect_status = QLabel()
        self._inspect_status.setStyleSheet("color: gray;")

        root.addWidget(self._type_label)
        root.addWidget(self._path_label)
        root.addWidget(self._sizes_label)
        root.addWidget(self._warning_label)
        root.addWidget(self._inspect_status)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

    def refresh(self) -> None:
        self._refresh_btn.setEnabled(False)
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.blockSignals(False)
        self._themes.clear()
        self._path_label.clear()
        self._type_label.clear()
        self._sizes_label.clear()
        self._warning_label.hide()
        self._inspect_status.setText("Scanning themes...")

        scanner = ThemeScanner()
        themes = scanner.scan()
        self._themes = themes

        self._combo.blockSignals(True)
        for t in themes:
            self._combo.addItem(t.display_label())
        self._combo.blockSignals(False)

        if themes:
            self._inspect_status.setText("")
            self._on_index_changed(0)
        else:
            self._inspect_status.setText("No cursor themes found.")

        self._refresh_btn.setEnabled(True)

    def _on_index_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._themes):
            return
        theme = self._themes[index]
        self._path_label.setText(f"Path: {theme.path}")
        self._type_label.setText(f"Location: {theme.source_type.label()}")
        self._sizes_label.setText("Existing sizes: inspecting...")
        self._warning_label.hide()
        self._inspect_status.setText("")

        worker = _InspectWorker(theme)
        worker.signals.done.connect(self._on_inspect_done)
        worker.signals.error.connect(self._on_inspect_error)
        QThreadPool.globalInstance().start(worker)

    def _on_inspect_done(self, result: tuple[CursorTheme, str | None]) -> None:
        updated, warning = result
        sizes_str = (
            ", ".join(str(s) for s in updated.existing_sizes)
            if updated.existing_sizes
            else "unknown — is xcur2png installed?"
        )
        self._sizes_label.setText(f"Existing sizes: {sizes_str}")

        if warning:
            self._warning_label.setText(f"Warning: {warning}")
            self._warning_label.show()
        else:
            self._warning_label.hide()

        if updated.failed_inspections:
            self._inspect_status.setText(
                f"Inspected {updated.inspected_files} cursor(s), "
                f"{updated.failed_inspections} failed to read."
            )
        else:
            self._inspect_status.setText(
                f"Inspected {updated.inspected_files} cursor(s)."
            )

        self.theme_ready.emit(updated, warning)

    def _on_inspect_error(self, msg: str) -> None:
        self._sizes_label.setText("Existing sizes: inspection error")
        self._inspect_status.setText(f"Error: {msg}")

    def current_theme(self) -> CursorTheme | None:
        idx = self._combo.currentIndex()
        if 0 <= idx < len(self._themes):
            return self._themes[idx]
        return None
