# Ransomware Knowledge Base window for Kanvas: search ransomware.live API for victim
# information by company or organization name and display results.
# Reviewed on 01/02/2026 by Jinto Antony

import logging

import requests
from PySide6.QtCore import Qt
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

RANSOMWARE_API_BASE = "https://api.ransomware.live/v2/searchvictims"
REQUEST_TIMEOUT = 10

VICTIM_FIELDS = [
    ("victim", "Victim", "Unknown"),
    ("group", "Group", "Unknown"),
    ("country", "Country", "Unknown"),
    ("discovered", "Discovered", "Unknown"),
    ("domain", "Domain", "Unknown"),
    ("description", "Description", "None"),
    ("attackdate", "Attack Date", "Unknown"),
    ("claim_url", "Claim URL", "None"),
    ("screenshot", "Screenshot", "None"),
    ("activity", "Activity", "None"),
    ("infostealer", "Infostealer", "None"),
    ("duplicates", "Duplicates", "None"),
    ("extrainfos", "Extra Infos", "None"),
    ("press", "Press", "None"),
]


def open_ransomware_kb_window(parent_window):
    kb_window = QWidget(parent_window.window)
    kb_window.setWindowTitle("Ransomware Victim Lookups")
    kb_window.resize(720, 600)
    kb_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )

    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("Victim Name:")
    input_label.setStyleSheet(styles.LABEL_FONT_12PT)
    input_layout.addWidget(input_label)

    victim_entry = QLineEdit()
    victim_entry.setPlaceholderText("Enter company or organization name")
    victim_entry.setStyleSheet(styles.LABEL_FONT_10PT)
    victim_entry.setMinimumWidth(300)
    input_layout.addWidget(victim_entry)

    search_button = QPushButton("Search")
    search_button.setFixedWidth(100)
    search_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    input_layout.addWidget(search_button)

    main_layout.addLayout(input_layout)

    results_label = QLabel("Results:")
    results_label.setStyleSheet(styles.LABEL_FONT_12PT)
    results_label.setContentsMargins(0, 10, 0, 5)
    main_layout.addWidget(results_label)

    result_text = QTextEdit()
    result_text.setStyleSheet(styles.LABEL_FONT_10PT)
    result_text.setReadOnly(True)
    main_layout.addWidget(result_text, 1)

    button_layout = QHBoxLayout()
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet(styles.BUTTON_STYLE_GREY)
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)

    def search_victim():
        victim_user = victim_entry.text().strip()
        if not victim_user:
            QMessageBox.warning(
                kb_window, "Warning", "Please enter a victim name."
            )
            return
        result_text.clear()
        try:
            api_url = f"{RANSOMWARE_API_BASE}/{victim_user}"
            response = requests.get(
                api_url, timeout=REQUEST_TIMEOUT
            )
            if response.status_code != 200:
                logger.error(
                    "API request failed with status code %s for victim: %s",
                    response.status_code,
                    victim_user,
                )
                result_text.append(
                    f"Error: API request failed with status code "
                    f"{response.status_code}."
                )
                return
            data = response.json()
            if isinstance(data, dict):
                victims = [data]
            elif isinstance(data, list):
                victims = data
            else:
                logger.error(
                    "Unexpected data format received from ransomware API"
                )
                result_text.append(
                    "Unexpected data format received from the API."
                )
                return
            if not victims:
                logger.info(
                    "No victims found for search term: %s", victim_user
                )
                result_text.append("No victims found.")
                return
            for victim in victims:
                for key, label, default in VICTIM_FIELDS:
                    value = victim.get(key, default)
                    result_text.append(f"{label}: {value}")
                result_text.append("-" * 50)
        except requests.exceptions.Timeout:
            logger.error(
                "API request timeout for victim: %s", victim_user
            )
            QMessageBox.critical(
                kb_window,
                "Error",
                "The request timed out. Please try again later.",
            )
        except requests.exceptions.ConnectionError:
            logger.error(
                "Connection error during API request for victim: %s",
                victim_user,
            )
            QMessageBox.critical(
                kb_window,
                "Error",
                "Failed to connect to the API. "
                "Please check your internet connection.",
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                "Request exception during API call for victim %s: %s",
                victim_user,
                e,
            )
            QMessageBox.critical(
                kb_window, "Error", f"An error occurred: {e}"
            )
        except Exception as e:
            logger.error(
                "Unexpected error during ransomware search for victim %s: %s",
                victim_user,
                e,
            )
            QMessageBox.critical(
                kb_window, "Error", f"Unexpected error: {e}"
            )

    search_button.clicked.connect(search_victim)
    close_button.clicked.connect(kb_window.close)
    victim_entry.returnPressed.connect(search_victim)
    kb_window.show()
    return kb_window
