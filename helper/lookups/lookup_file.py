# File Hash Lookup window for Kanvas: look up file hashes (MD5, SHA-1, SHA-256) via
# VirusTotal API and provide quick links to VT, OTX, Joe Sandbox, Any.Run, and others.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import webbrowser

import requests
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
from helper.api_config import get_api_key

logger = logging.getLogger(__name__)

VT_FILES_API = "https://www.virustotal.com/api/v3/files"
REQUEST_TIMEOUT = 15

HASH_BUTTON_NAMES = [
    "VT",
    "OTX",
    "Joesandbox",
    "Any.Run",
    "Talos",
    "HybridAnalysis",
    "Cymru",
    "ThreatFox",
]
HASH_URL_TEMPLATES = {
    "VT": "https://www.virustotal.com/gui/file/{hash}",
    "OTX": "https://otx.alienvault.com/indicator/file/{hash}",
    "Joesandbox": "https://www.joesandbox.com/",
    "Any.Run": "https://app.any.run/submissions",
    "Talos": "https://talosintelligence.com/",
    "HybridAnalysis": "https://www.hybrid-analysis.com/",
    "Cymru": "https://hash.cymru.com/",
    "ThreatFox": "https://threatfox.abuse.ch/browse/",
}

active_hash_window = None


def open_hash_lookup_window(parent, db_path):
    global active_hash_window
    if active_hash_window is not None and not active_hash_window.isHidden():
        active_hash_window.raise_()
        active_hash_window.activateWindow()
        return active_hash_window

    hash_window = QWidget(parent.window)
    hash_window.setWindowTitle("File Hash Lookup")
    hash_window.resize(720, 600)
    hash_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )

    main_layout = QVBoxLayout(hash_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("File Hash:")
    input_label.setFont(QFont("Arial", 12))
    input_layout.addWidget(input_label)

    hash_entry = QLineEdit()
    hash_entry.setFont(QFont("Arial", 10))
    hash_entry.setMinimumWidth(300)
    hash_entry.setPlaceholderText("MD5, SHA-1, SHA-256")
    input_layout.addWidget(hash_entry)

    submit_button = QPushButton("Search")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    input_layout.addWidget(submit_button)

    main_layout.addLayout(input_layout)

    buttons_layout = QHBoxLayout()
    for name in HASH_BUTTON_NAMES:
        button = QPushButton(name)
        button.setStyleSheet(styles.BUTTON_STYLE_PINK)

        def make_handler(url_template):
            def handler():
                if "{hash}" in url_template:
                    hash_value = hash_entry.text().strip()
                    if not hash_value:
                        QMessageBox.warning(
                            hash_window,
                            "Warning",
                            "Please enter a hash value first.",
                        )
                        return
                    url = url_template.format(hash=hash_value)
                else:
                    url = url_template
                webbrowser.open(url)

            return handler

        button.clicked.connect(make_handler(HASH_URL_TEMPLATES[name]))
        buttons_layout.addWidget(button)

    main_layout.addLayout(buttons_layout)

    results_label = QLabel("Result:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 10, 0, 5)

    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
    result_text.setReadOnly(True)

    main_layout.addWidget(results_label)
    main_layout.addWidget(result_text, 1)

    button_layout = QHBoxLayout()
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet(styles.BUTTON_STYLE_GREY)
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)

    def get_vt_api_key():
        key = get_api_key("VT_API_KEY")
        if not key:
            QMessageBox.warning(
                hash_window,
                "API Key Missing",
                "VirusTotal API key not found in settings.\n"
                "Please add your API key in API Settings.",
            )
        return key

    def submit_hash():
        hash_value = hash_entry.text().strip()
        if not hash_value:
            QMessageBox.warning(
                hash_window, "Warning", "Please enter a hash value."
            )
            return
        submit_button.setEnabled(False)
        submit_button.setText("Searching...")
        hash_entry.setEnabled(False)
        result_text.clear()
        result_text.append("Contacting VirusTotal API...")
        try:
            vt_api_key = get_vt_api_key()
            if not vt_api_key:
                return
            url = f"{VT_FILES_API}/{hash_value}"
            headers = {"x-apikey": vt_api_key}
            response = requests.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT
            )
            result_text.clear()
            if response.status_code == 200:
                data = response.json().get("data", {}).get("attributes", {})
                result_text.append(
                    f"Reputation: {data.get('reputation', 'N/A')}"
                )
                result_text.append(
                    f"Last Analysis Date: {data.get('last_analysis_date', 'N/A')}"
                )
                result_text.append("\nLast Analysis Stats:")
                stats = data.get("last_analysis_stats", {})
                for key in [
                    "harmless",
                    "malicious",
                    "suspicious",
                    "undetected",
                    "timeout",
                ]:
                    result_text.append(
                        f"  {key.capitalize()}: {stats.get(key, 0)}"
                    )
                result_text.append("\nAdditional Information:")
                result_text.append(
                    f"  Magic: {data.get('magic', 'N/A')}"
                )
                result_text.append(
                    f"  File Type: {data.get('type_description', 'N/A')}"
                )
                result_text.append(
                    f"  File Size: {data.get('size', 'N/A')} bytes"
                )
            else:
                logger.error(
                    "VirusTotal API request failed with status code %s for hash: %s...",
                    response.status_code,
                    hash_value[:8],
                )
                error_msg = response.json().get("error", {}).get(
                    "message", "No error message provided"
                )
                result_text.append(
                    f"Error: VirusTotal API request failed with "
                    f"status code {response.status_code}"
                )
                result_text.append(error_msg)
        except Exception as e:
            logger.error("Exception during hash submission: %s", e)
            result_text.append(f"Error: {e}")
        finally:
            submit_button.setEnabled(True)
            submit_button.setText("Search")
            hash_entry.setEnabled(True)

    def handle_close_event(event):
        global active_hash_window
        active_hash_window = None
        event.accept()

    submit_button.clicked.connect(submit_hash)
    hash_entry.returnPressed.connect(submit_hash)
    close_button.clicked.connect(hash_window.close)
    hash_window.closeEvent = handle_close_event
    active_hash_window = hash_window
    hash_window.show()
    return hash_window
