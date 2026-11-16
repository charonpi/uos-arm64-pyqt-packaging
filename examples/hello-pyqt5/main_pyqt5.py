#!/usr/bin/env python3
"""AFTER sample: the same app migrated to PyQt5 + Python 3.7.

This is what the migration script produces (plus manual review). It runs on
UOS 20 arm64 with the system `python3-pyqt5`, no pip-installed Qt anywhere.
"""
from __future__ import annotations

# uos-arm64-pyqt-packaging bootstrap (generated) - keep before business imports
import os as _uos_os
import sys as _uos_sys
_UOS_HERE = _uos_os.path.dirname(_uos_os.path.abspath(__file__))
if _UOS_HERE not in _uos_sys.path:
    _uos_sys.path.insert(0, _UOS_HERE)
_UOS_VENDOR = _uos_os.path.join(_UOS_HERE, "third_party")
if _UOS_VENDOR not in _uos_sys.path:
    _uos_sys.path.insert(0, _UOS_VENDOR)
# end uos-arm64-pyqt-packaging bootstrap

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget, QMessageBox)
from PyQt5.QtCore import Qt


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UOS arm64 demo")
        central = QWidget()
        layout = QVBoxLayout(central)
        self.button = QPushButton("Export Excel")
        self.button.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.button, alignment=Qt.AlignCenter)
        self.button.clicked.connect(self.on_click)
        self.setCentralWidget(central)

    def on_click(self) -> None:
        QMessageBox.information(self, "Done", "Packaged with python3-pyqt5",
                                QMessageBox.Ok)


def main(items: list[str] | None = None) -> None:
    app = QApplication([])
    win = Window()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
