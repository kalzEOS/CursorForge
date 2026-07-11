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
PRESET_FINE = frozenset((16, 20, 22, 24, 28, 32, 36, 40, 42, 44, 48, 56, 64, 72, 80, 88, 96, 112, 128))


class SizePanel(QGroupBox):
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Target Sizes", parent)
        self._existing: frozenset[int] = frozenset()
        self._boxes: dict[int, QCheckBox] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(160)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setSpacing(4)

        grid = QGridLayout()
        grid.setSpacing(4)
        cols = 6
        for i, size in enumerate(ALL_SIZES):
            cb = QCheckBox(str(size))
            cb.stateChanged.connect(self.selection_changed.emit)
            self._boxes[size] = cb
            grid.addWidget(cb, i // cols, i % cols)

        container = QWidget()
        container.setLayout(grid)
        scroll.setWidget(container)
        root.addWidget(scroll)

        # legend
        legend = QLabel(
            "<font color='gray'>Grayed = already in theme. "
            "Checked = will be generated.</font>"
        )
        legend.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(legend)

        # action buttons
        btn_row = QHBoxLayout()
        for label, slot in (
            ("Select All", self._select_all),
            ("Clear Additions", self._clear_additions),
            ("BreezeX Preset", self._apply_breezex),
            ("Fine-grained Preset", self._apply_fine),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        root.addLayout(btn_row)

        # custom size entry
        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom sizes (comma-separated):"))
        self._custom_edit = QLineEdit()
        self._custom_edit.setPlaceholderText("e.g. 18, 26, 100")
        custom_row.addWidget(self._custom_edit)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_custom)
        custom_row.addWidget(add_btn)
        root.addLayout(custom_row)

        self._custom_sizes: set[int] = set()

    def set_existing_sizes(self, sizes: tuple[int, ...]) -> None:
        self._existing = frozenset(sizes)
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
        self.selection_changed.emit()

    def selected_sizes(self) -> list[int]:
        result: list[int] = list(self._existing)
        for size, cb in self._boxes.items():
            if cb.isChecked() and size not in self._existing:
                result.append(size)
        result.extend(self._custom_sizes - self._existing)
        return sorted(set(result))

    def new_sizes(self) -> list[int]:
        """Sizes to generate (not already in the theme)."""
        selected = set(self.selected_sizes())
        return sorted(selected - self._existing)

    def _select_all(self) -> None:
        for cb in self._boxes.values():
            if cb.isEnabled():
                cb.setChecked(True)

    def _clear_additions(self) -> None:
        for size, cb in self._boxes.items():
            if size not in self._existing:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._custom_sizes.clear()
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

    def _apply_fine(self) -> None:
        self._apply_preset(PRESET_FINE)

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

        self._custom_sizes.update(parsed)
        self._custom_edit.clear()
        self.selection_changed.emit()
