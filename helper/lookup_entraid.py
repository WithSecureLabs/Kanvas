import sqlite3
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QMessageBox
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

def open_entra_lookup_window(parent, db_path):
    entra_window = QWidget(parent)
    entra_window.setWindowTitle("Entra AppID Lookup")
    entra_window.resize(720, 600)
    entra_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    main_layout = QVBoxLayout(entra_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    input_label = QLabel("Enter AppID:")
    input_label.setFont(QFont("Arial", 12))
    main_layout.addWidget(input_label)
    appid_entry = QLineEdit()
    appid_entry.setFont(QFont("Arial", 10))
    appid_entry.setMinimumWidth(550)
    appid_entry.setPlaceholderText("31d3f3f5-7267-45a8-9549-affb00110054")
    main_layout.addWidget(appid_entry)
    results_label = QLabel("Results:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 10, 0, 5)
    main_layout.addWidget(results_label)
    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
    result_text.setReadOnly(True)
    main_layout.addWidget(result_text, 1)
    button_frame = QWidget()
    button_layout = QHBoxLayout(button_frame)
    button_layout.setContentsMargins(0, 10, 0, 0)
    submit_button = QPushButton("Submit")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet("background-color: #4CAF50; color: white;")
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    button_layout.addStretch()
    button_layout.addWidget(submit_button)
    button_layout.addSpacing(20)
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addWidget(button_frame)
    
    def fetch_appid_info():
        appid = appid_entry.text().strip()
        if not appid:
            QMessageBox.warning(entra_window, "Warning", "Please enter an AppID.")
            return
        result_text.clear()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT AppDisplayName FROM entra_appid WHERE AppId = ?", (appid,))
            row = cursor.fetchone()
            if row:
                result_text.append(f"AppDisplayName: {row[0]}")
            else:
                result_text.append("No AppDisplayName found for the given AppID.")
        except sqlite3.Error as e:
            logger.error(f"Database error occurred: {e}")
            result_text.append(f"Database error: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
                logger.info("Database connection closed")
    
    submit_button.clicked.connect(fetch_appid_info)
    close_button.clicked.connect(entra_window.close)
    appid_entry.returnPressed.connect(fetch_appid_info)
    entra_window.show()
    return entra_window