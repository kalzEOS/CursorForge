from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

ALL_SIZES = (16, 20, 22, 24, 28, 32, 36, 40, 42, 44, 48, 56, 64, 72, 80, 88, 96, 112, 128)

PRESET_BREEZEX = frozenset((16, 20, 22, 24, 28, 32, 40, 48, 56, 64, 72, 80, 88, 96))

_COLS = 6


class SizePanel(QGroupBox):
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Target Sizes", parent)
        self._existing: frozenset[int] = frozenset()
        self._boxes: dict[int, QCheckBox] = {}
        self._grid: QGridLayout | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(240)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        container = QWidget()
        self._grid = QGridLayout(container)
        self._grid.setSpacing(4)

        for size in ALL_SIZES:
            self._add_checkbox(size)

        self._scroll.setWidget(container)
        root.addWidget(self._scroll)

        legend = QLabel(
            "<font color='gray'>Grayed = already in theme. "
            "Checked = will be generated. "
            "Custom sizes are added to the list above.</font>"
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(legend)

        btn_row = QHBoxLayout()
        for label, slot in (
            ("Select All", self._select_all),
            ("Clear Additions", self._clear_additions),
            ("BreezeX Preset", self._apply_breezex),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        root.addLayout(btn_row)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom sizes (comma-separated):"))
        self._custom_edit = QLineEdit()
        self._custom_edit.setPlaceholderText("e.g. 18, 26, 100")
        self._custom_edit.returnPressed.connect(self._add_custom)
        custom_row.addWidget(self._custom_edit)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_custom)
        custom_row.addWidget(add_btn)
        root.addLayout(custom_row)

    def _add_checkbox(self, size: int, checked: bool = False) -> QCheckBox:
        assert self._grid is not None
        cb = QCheckBox(str(size))
        cb.setChecked(checked)
        cb.stateChanged.connect(lambda _: self.selection_changed.emit())
        self._boxes[size] = cb

        # Place in sorted position — recompute all positions
        self._reflow_grid()
        return cb

    def _reflow_grid(self) -> None:
        assert self._grid is not None
        sorted_sizes = sorted(self._boxes)
        for i, size in enumerate(sorted_sizes):
            cb = self._boxes[size]
            self._grid.addWidget(cb, i // _COLS, i % _COLS)

    def set_existing_sizes(self, sizes: tuple[int, ...]) -> None:
        self._existing = frozenset(sizes)

        # Add checkboxes for existing sizes not covered by ALL_SIZES or custom entries
        for size in self._existing:
            if size not in self._boxes:
                self._add_checkbox(size)

        for size, cb in self._boxes.items():
            cb.blockSignals(True)
            if size in self._existing:
                cb.setChecked(True)
                cb.setText(f"{size} (existing)")
                cb.setEnabled(False)
            else:
                cb.setChecked(False)
                cb.setText(str(size))
                cb.setEnabled(True)
            cb.blockSignals(False)
        self._reflow_grid()
        self.selection_changed.emit()

    def selected_sizes(self) -> list[int]:
        return sorted(
            size for size, cb in self._boxes.items() if cb.isChecked()
        )

    def new_sizes(self) -> list[int]:
        return sorted(
            size for size, cb in self._boxes.items()
            if cb.isChecked() and size not in self._existing
        )

    def _select_all(self) -> None:
        for cb in self._boxes.values():
            if cb.isEnabled():
                cb.setChecked(True)

    def _clear_additions(self) -> None:
        # Remove custom checkboxes (not in ALL_SIZES)
        for size in list(self._boxes):
            if size not in ALL_SIZES:
                cb = self._boxes.pop(size)
                cb.deleteLater()

        for size, cb in self._boxes.items():
            if size not in self._existing:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self.selection_changed.emit()

    def _apply_preset(self, preset: frozenset[int]) -> None:
        for size, cb in self._boxes.items():
            if cb.isEnabled():
                cb.blockSignals(True)
                cb.setChecked(size in preset)
                cb.blockSignals(False)
        self.selection_changed.emit()

    def _apply_breezex(self) -> None:
        self._apply_preset(PRESET_BREEZEX)

    def _add_custom(self) -> None:
        text = self._custom_edit.text().strip()
        if not text:
            return
        errors: list[str] = []
        parsed: list[int] = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                val = int(part)
                if not (8 <= val <= 256):
                    errors.append(f"{val} is out of range (8–256)")
                else:
                    parsed.append(val)
            except ValueError:
                errors.append(f"{part!r} is not an integer")

        if errors:
            QMessageBox.warning(self, "Invalid Sizes", "\n".join(errors))
            return

        added = False
        for val in parsed:
            if val in self._boxes:
                # Already in list — just check it if not existing
                cb = self._boxes[val]
                if cb.isEnabled():
                    cb.setChecked(True)
            else:
                self._add_checkbox(val, checked=True)
                added = True

        self._custom_edit.clear()
        if added:
            self._reflow_grid()
        self.selection_changed.emit()
