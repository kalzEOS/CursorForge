from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from cursorforge.dependencies import all_available, check_dependencies
from cursorforge.paths import LOG_DIR
from cursorforge.ui.dependency_dialog import DependencyDialog
from cursorforge.ui.main_window import MainWindow

log = logging.getLogger(__name__)


def _setup_file_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "cursorforge.log"
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.DEBUG)


def run() -> int:
    _setup_file_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("CursorForge")
    app.setApplicationVersion("0.1.0")

    statuses = check_dependencies()
    if not all_available(statuses):
        dialog = DependencyDialog(statuses)
        dialog.exec()
        # Allow the app to continue even with missing deps — user may install them
        # and the parts that need them will degrade gracefully.

    window = MainWindow()
    window.show()

    return app.exec()