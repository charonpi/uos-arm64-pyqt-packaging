#!/usr/bin/env python3
"""BEFORE sample: a PyQt6-style app, used to demo the migration script.

Copy this file into a scratch directory and run:
    python3 scripts/migrate_pyqt6_to_pyqt5.py <scratch> --dry-run
"""
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget, QMessageBox)
from PyQt6.QtCore import Qt


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UOS arm64 demo")
        central = QWidget()
        layout = QVBoxLayout(central)
        self.button = QPushButton("Export Excel")
        self.button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.button.clicked.connect(self.on_click)
        self.setCentralWidget(central)

    def on_click(self) -> None:
        QMessageBox.information(self, "Done", "Packaged with python3-pyqt5",
                                QMessageBox.StandardButton.Ok)


def main() -> None:
    app = QApplication([])
    win = Window()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
