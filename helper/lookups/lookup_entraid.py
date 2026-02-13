# Entra AppID Lookup window for Kanvas: look up Microsoft Entra/Azure application IDs
# in the local database and display application details including display name and status.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from helper import styles

logger = logging.getLogger(__name__)


def build_result_html(row):
    status_color = (
        styles.HTML_SUCCESS_COLOR
        if row[3] == "MicrosoftApps.csv"
        else styles.HTML_DANGER_COLOR
    )
    status_text = (
        "Legitimate" if row[3] == "MicrosoftApps.csv" else "Malicious"
    )
    return f"""
    <div style="font-family: Arial; font-size: 11pt; line-height: 1.4;">
        <h3 style="color: #2c3e50; margin-bottom: 10px;">Application Details</h3>
        <table style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f8f9fa;">
                <td style="padding: 8px; border: 1px solid #dee2e6; font-weight: bold; width: 30%;">App ID:</td>
                <td style="padding: 8px; border: 1px solid #dee2e6; font-family: monospace;">{row[0]}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #dee2e6; font-weight: bold;">Display Name:</td>
                <td style="padding: 8px; border: 1px solid #dee2e6;">{row[1]}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #dee2e6; font-weight: bold;">Status:</td>
                <td style="padding: 8px; border: 1px solid #dee2e6; color: {status_color}; font-weight: bold;">{status_text}</td>
            </tr>
        </table>
    </div>
    """


def build_no_results_html(appid):
    return f"""
    <div style="font-family: Arial; font-size: 11pt; text-align: center; padding: 20px;">
        <h3 style="color: {styles.HTML_DANGER_COLOR}; margin-bottom: 10px;">No Results Found</h3>
        <p style="color: #6c757d;">No application found for AppID: <code style="background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px;">{appid}</code></p>
    </div>
    """


def build_error_html(message):
    return f"""
    <div style="font-family: Arial; font-size: 11pt; text-align: center; padding: 20px;">
        <h3 style="color: {styles.HTML_DANGER_COLOR}; margin-bottom: 10px;">Database Error</h3>
        <p style="color: #6c757d;">{message}</p>
    </div>
    """


def open_entra_lookup_window(parent, db_path):
    entra_window = QWidget(parent)
    entra_window.setWindowTitle("Entra AppID Lookup")
    entra_window.resize(720, 600)
    entra_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )

    main_layout = QVBoxLayout(entra_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("Entra/ AzureAppID:")
    input_label.setFont(QFont("Arial", 12))
    input_layout.addWidget(input_label)

    appid_entry = QLineEdit()
    appid_entry.setFont(QFont("Arial", 10))
    appid_entry.setMinimumWidth(300)
    appid_entry.setPlaceholderText("31d3f3f5-7267-45a8-9549-affb00110054")
    input_layout.addWidget(appid_entry)

    submit_button = QPushButton("Search")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    input_layout.addWidget(submit_button)

    main_layout.addLayout(input_layout)

    results_label = QLabel("Results:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 5, 0, 0)
    main_layout.addWidget(results_label)

    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
    result_text.setReadOnly(True)
    result_text.setMaximumHeight(200)
    main_layout.addWidget(result_text, 1)

    button_layout = QHBoxLayout()
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet(styles.BUTTON_STYLE_GREY)
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)

    def fetch_appid_info():
        appid = appid_entry.text().strip()
        if not appid:
            QMessageBox.warning(
                entra_window, "Warning", "Please enter an AppID."
            )
            return
        result_text.clear()
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT AppId, AppDisplayName, Source, FileName FROM entra_appid WHERE AppId = ?",
                (appid,),
            )
            row = cursor.fetchone()
            if row:
                result_text.setHtml(build_result_html(row))
            else:
                result_text.setHtml(build_no_results_html(appid))
        except sqlite3.Error as e:
            logger.error("Database error occurred: %s", e)
            result_text.setHtml(build_error_html(str(e)))
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed")

    submit_button.clicked.connect(fetch_appid_info)
    close_button.clicked.connect(entra_window.close)
    appid_entry.returnPressed.connect(fetch_appid_info)
    entra_window.show()
    return entra_window
