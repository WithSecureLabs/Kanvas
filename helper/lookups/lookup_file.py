# code reviewed 
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import requests
import sqlite3
import logging
import webbrowser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

_active_window = None

def open_hash_lookup_window(parent, db_path):
    global _active_window
    if _active_window is not None and not _active_window.isHidden():
        _active_window.raise_()
        _active_window.activateWindow()
        return _active_window
    hash_window = QWidget(parent.window)
    hash_window.setWindowTitle("File Hash Lookup")
    hash_window.resize(720, 600)
    hash_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
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
    submit_button.setStyleSheet("background-color: #4CAF50; color: white;")
    input_layout.addWidget(submit_button)
    main_layout.addLayout(input_layout)
    buttons_layout = QHBoxLayout()
    button_names = ["VT", "OTX", "Joesandbox", "Any.Run", "Talos", "HybridAnalysis","Cymru" , "ThreatFox"]
    button_style = """
        QPushButton {
            background-color: #FF69B4;
            color: white;
            border-radius: 4px;
            padding: 5px 10px;
            font-weight: normal;
        }
        QPushButton:hover {
            background-color: #FF1493;
        }
        QPushButton:pressed {
            background-color: #C71585;
        }
    """
    url_templates = {
        "VT": "https://www.virustotal.com/gui/file/{hash}",
        "OTX": "https://otx.alienvault.com/indicator/file/{hash}",
        "Joesandbox": "https://www.joesandbox.com/",
        "Any.Run": "https://app.any.run/submissions",
        "Talos": "https://talosintelligence.com/",
        "HybridAnalysis": "https://www.hybrid-analysis.com/",
        "Cymru": "https://hash.cymru.com/",
        "ThreatFox": "https://threatfox.abuse.ch/browse/"
    }
    def create_button_click_handler(name, url_template):
        def button_click_handler():
            if "{hash}" in url_template:
                hash_value = hash_entry.text().strip()
                if not hash_value:
                    QMessageBox.warning(hash_window, "Warning", "Please enter a hash value first.")
                    return
                url = url_template.format(hash=hash_value)
            else:
                url = url_template
            webbrowser.open(url)
        return button_click_handler
    for name in button_names:
        button = QPushButton(name)
        button.setStyleSheet(button_style)
        button.clicked.connect(create_button_click_handler(name, url_templates[name]))
        buttons_layout.addWidget(button)
    results_label = QLabel("Result:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 10, 0, 5)
    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
    result_text.setReadOnly(True)
    main_layout.addLayout(buttons_layout)
    main_layout.addWidget(results_label)
    main_layout.addWidget(result_text, 1)
    button_layout = QHBoxLayout()
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet("background-color: #d3d3d3; color: black;")
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)
    def get_vt_api_key():
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT VT_API_KEY FROM user_settings WHERE id = 1")
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
                else:
                    QMessageBox.warning(hash_window, "API Key Missing", "VirusTotal API key not found in settings.\nPlease add your API key in API Settings.")
                    return None
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving API key: {e}")
            QMessageBox.critical(hash_window, "Error", f"Failed to retrieve API key: {e}")
            return None
    def submit_hash():
        hash_value = hash_entry.text().strip()
        if not hash_value:
            QMessageBox.warning(hash_window, "Warning", "Please enter a hash value.")
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
            url = f"https://www.virustotal.com/api/v3/files/{hash_value}"
            headers = {"x-apikey": vt_api_key}
            response = requests.get(url, headers=headers)
            result_text.clear()
            if response.status_code == 200:
                data = response.json().get("data", {}).get("attributes", {})
                result_text.append(f"Reputation: {data.get('reputation', 'N/A')}")
                result_text.append(f"Last Analysis Date: {data.get('last_analysis_date', 'N/A')}")
                result_text.append("\nLast Analysis Stats:")
                stats = data.get("last_analysis_stats", {})
                for key in ["harmless", "malicious", "suspicious", "undetected", "timeout"]:
                    result_text.append(f"  {key.capitalize()}: {stats.get(key, 0)}")
                result_text.append("\nAdditional Information:")
                result_text.append(f"  Magic: {data.get('magic', 'N/A')}")
                result_text.append(f"  File Type: {data.get('type_description', 'N/A')}")
                result_text.append(f"  File Size: {data.get('size', 'N/A')} bytes")
            else:
                logger.error(f"VirusTotal API request failed with status code {response.status_code} for hash: {hash_value[:8]}...")
                error_msg = response.json().get("error", {}).get("message", "No error message provided")
                result_text.append(f"Error: VirusTotal API request failed with status code {response.status_code}")
                result_text.append(error_msg)
        except Exception as e:
            logger.error(f"Exception during hash submission: {e}")
            result_text.append(f"Error: {e}")
        finally:
            submit_button.setEnabled(True)
            submit_button.setText("Submit")
            hash_entry.setEnabled(True)
    def handle_close_event(event):
        global _active_window
        _active_window = None
        event.accept()
    submit_button.clicked.connect(submit_hash)
    hash_entry.returnPressed.connect(submit_hash)
    close_button.clicked.connect(hash_window.close)
    hash_window.closeEvent = handle_close_event
    _active_window = hash_window
    hash_window.show()
    return hash_window