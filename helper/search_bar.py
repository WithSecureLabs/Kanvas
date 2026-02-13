"""
Inline search bar widget for Kanvas: provides quick search in the main window
with optional case-sensitive matching and clear.
Revised on 01/02/2026 by Jinto Antony
"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from helper import styles

logger = logging.getLogger(__name__)


class SearchBarWidget(QWidget):
    search_requested = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        self.setMaximumHeight(50)
        self.setMinimumHeight(40)

        search_label = QLabel("Search:")
        search_label.setMinimumWidth(50)
        layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Quick search in current sheet...")
        self.search_input.returnPressed.connect(self.on_search)
        layout.addWidget(self.search_input, 1)

        self.case_checkbox = QCheckBox("Case")
        self.case_checkbox.setToolTip("Case sensitive search")
        layout.addWidget(self.case_checkbox)

        self.search_button = QPushButton("Search")
        self.search_button.setStyleSheet(styles.BUTTON_SEARCH_COMPACT)
        self.search_button.clicked.connect(self.on_search)
        layout.addWidget(self.search_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setStyleSheet(styles.BUTTON_CLEAR_MINIMAL)
        self.clear_button.clicked.connect(self.on_clear)
        layout.addWidget(self.clear_button)

    def on_search(self):
        search_term = self.search_input.text().strip()
        if search_term:
            case_sensitive = self.case_checkbox.isChecked()
            self.search_requested.emit(search_term, case_sensitive)

    def on_clear(self):
        self.search_input.clear()
        self.search_requested.emit("", False)

    def set_search_text(self, text: str):
        self.search_input.setText(text)
