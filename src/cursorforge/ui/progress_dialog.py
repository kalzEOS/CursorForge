from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from cursorforge.builder import BuildResult


class BuildProgressDialog(QDialog):
    """Modal dialog that shows build progress and the final result."""

    def __init__(self, theme_name: str, new_sizes: list[int], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Building Theme")
        self.setMinimumWidth(420)
        self._build_ui(theme_name, new_sizes)

    def _build_ui(self, theme_name: str, new_sizes: list[int]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._heading = QLabel(f"Building <b>{theme_name}</b>…")
        self._heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._heading)

        sizes_str = ", ".join(str(s) for s in new_sizes)
        self._detail = QLabel(f"Adding sizes: {sizes_str}")
        self._detail.setStyleSheet("color: gray;")
        self._detail.setWordWrap(True)
        layout.addWidget(self._detail)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._status = QLabel("Starting…")
        self._status.setStyleSheet("color: gray;")
        layout.addWidget(self._status)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._close_btn = self._buttons.button(QDialogButtonBox.StandardButton.Close)
        self._close_btn.setEnabled(False)
        self._buttons.rejected.connect(self.accept)
        layout.addWidget(self._buttons)

    def update_progress(self, message: str, current: int, total: int) -> None:
        self._status.setText(message)
        if total > 0:
            self._progress.setValue(int(current / total * 100))

    def show_result(self, result: BuildResult) -> None:
        """Update the dialog in place with the build result. Does not close it."""
        self._progress.setValue(100)
        self._status.hide()
        self._close_btn.setEnabled(True)
        self._close_btn.setFocus()

        if result.success:
            self._heading.setText("Build complete!")
            parts = [f"<b>Location:</b> {result.output_path}"]
            if result.sizes_added:
                parts.append(
                    f"<b>Sizes added:</b> {', '.join(str(s) for s in result.sizes_added)}"
                )
            parts.append(f"<b>Cursors processed:</b> {result.cursors_processed}")
            if result.cursors_failed:
                parts.append(
                    f"<font color='orange'>"
                    f"{result.cursors_failed} cursor(s) had errors — see log."
                    f"</font>"
                )
            self._detail.setText("<br>".join(parts))
            self._detail.setTextFormat(Qt.TextFormat.RichText)
            self._detail.setStyleSheet("")
        else:
            self._heading.setText("<font color='red'>Build failed.</font>")
            errors = result.errors[:5] or ["Unknown error."]
            self._detail.setText("\n".join(errors))
            self._detail.setStyleSheet("color: red;")
