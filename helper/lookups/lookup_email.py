# Email Lookup window for Kanvas: check email addresses against Have I Been Pwned (HIBP)
# API for data breaches, display breach details with formatted results.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import re
import urllib.parse

import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
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

HIBP_BREACH_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"
REQUEST_TIMEOUT = 15
HIBP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADER_PATTERNS = ["=== Breach Data ==="]
RISK_KEYWORDS_RED = ["breach(es)", "compromised"]
RISK_KEYWORDS_GREEN = ["clean"]

EMAIL_LOOKUP_WINDOW = None


def process_breach_data(breach_data):
    result = ["\n=== Breach Data ===\n"]
    if not breach_data:
        result.append("✓ No breaches found")
        return result
    result.append(
        f"⚠ Found {len(breach_data)} breach(es) for this email address:\n"
    )
    for i, breach in enumerate(breach_data, 1):
        result.append(f"▼ Breach {i}: {breach.get('Name', 'Unknown')}")
        title = breach.get("Title")
        if title and title != "N/A":
            result.append(f"  • Title: {title}")
        domain = breach.get("Domain")
        if domain and domain != "N/A":
            result.append(f"  • Domain: {domain}")
        breach_date = breach.get("BreachDate")
        if breach_date and breach_date != "N/A":
            result.append(f"  • Breach Date: {breach_date}")
        added_date = breach.get("AddedDate")
        if added_date and added_date != "N/A":
            result.append(f"  • Added Date: {added_date}")
        pwn_count = breach.get("PwnCount")
        if pwn_count:
            result.append(f"  • Pwn Count: {pwn_count:,}")
        if breach.get("IsVerified"):
            result.append("  • Verified: Yes")
        if breach.get("IsFabricated"):
            result.append("  • Fabricated: Yes")
        if breach.get("IsSensitive"):
            result.append("  • Sensitive: Yes")
        if breach.get("IsRetired"):
            result.append("  • Retired: Yes")
        if breach.get("IsSpamList"):
            result.append("  • Spam List: Yes")
        if breach.get("IsMalware"):
            result.append("  • Malware: Yes")
        if breach.get("IsStealerLog"):
            result.append("  • Stealer Log: Yes")
        data_classes = breach.get("DataClasses", [])
        if data_classes:
            result.append("  • Data Classes Exposed:")
            for data_class in data_classes:
                result.append(f"    - {data_class}")
        description = breach.get("Description", "")
        if description:
            clean_desc = re.sub(r"<[^>]+>", "", description)
            clean_desc = (
                clean_desc.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
            )
            suffix = "..." if len(clean_desc) > 200 else ""
            result.append(f"  • Description: {clean_desc[:200]}{suffix}")
        if i < len(breach_data):
            result.append("  " + "─" * 40)
    return result


def fetch_hibp_data_synchronous(email_address, api_key):
    try:
        logger.info("Starting HIBP lookup")
        headers = {
            "hibp-api-key": api_key,
            "user-agent": HIBP_USER_AGENT,
        }
        breach_result = []
        breach_url = f"{HIBP_BREACH_URL}/{urllib.parse.quote(email_address)}"
        try:
            breach_response = requests.get(
                breach_url, headers=headers, timeout=REQUEST_TIMEOUT
            )
            if breach_response.status_code == 200:
                breach_data = breach_response.json()
                breach_result = process_breach_data(breach_data)
                logger.info(
                    "Found %d breaches for %s", len(breach_data), email_address
                )
            elif breach_response.status_code == 404:
                breach_result = [
                    "\n=== Breach Data ===\n",
                    "✓ No breaches found - Email address has not been "
                    "compromised in any known data breaches",
                ]
            elif breach_response.status_code == 401:
                breach_result = [
                    "\n=== Breach Data ===\n",
                    "❌ Error: Invalid HIBP API key",
                ]
            elif breach_response.status_code == 429:
                retry_after = breach_response.headers.get("retry-after", "60")
                breach_result = [
                    "\n=== Breach Data ===\n",
                    f"⚠ Rate limit exceeded. Try again in {retry_after} seconds",
                ]
            else:
                breach_result = [
                    "\n=== Breach Data ===\n",
                    f"❌ Error: HTTP {breach_response.status_code} - "
                    f"{breach_response.text}",
                ]
        except requests.RequestException as e:
            logger.error("HIBP breach API error: %s", e)
            breach_result = [
                "\n=== Breach Data ===\n",
                f"❌ Error: Connection error - {e}",
            ]
        except Exception as e:
            logger.error("HIBP unexpected error: %s", e)
            breach_result = ["\n=== Breach Data ===\n", f"❌ Error: {e}"]
        return "\n".join(breach_result)
    except Exception as e:
        logger.error(
            "Unexpected error during email lookup for %s: %s",
            email_address,
            e,
        )
        return f"Unexpected error: {e}"


def highlight_headers(text_edit):
    try:
        format_orange = QTextCharFormat()
        format_orange.setBackground(QColor(styles.HEADER_HIGHLIGHT_BG))
        format_orange.setForeground(QColor(styles.HEADER_HIGHLIGHT_FG))
        font = QFont("Arial", 10)
        font.setBold(True)
        format_orange.setFont(font)
        format_red = QTextCharFormat()
        format_red.setBackground(QColor(styles.KEYWORD_HIGHLIGHT_BG))
        format_red.setForeground(QColor(styles.KEYWORD_HIGHLIGHT_FG))
        format_red.setFont(font)
        format_green = QTextCharFormat()
        format_green.setBackground(QColor(styles.SUCCESS_HIGHLIGHT_BG))
        format_green.setForeground(QColor(styles.SUCCESS_HIGHLIGHT_FG))
        format_green.setFont(font)
        doc_text = text_edit.toPlainText()
        for base_header in HEADER_PATTERNS:
            index = 0
            while True:
                index = doc_text.find(base_header, index)
                if index == -1:
                    break
                cursor = text_edit.textCursor()
                cursor.setPosition(index)
                cursor.movePosition(
                    QTextCursor.Right, QTextCursor.KeepAnchor, len(base_header)
                )
                cursor.mergeCharFormat(format_orange)
                index += len(base_header)
        for keyword in RISK_KEYWORDS_RED + RISK_KEYWORDS_GREEN:
            index = 0
            while True:
                index = doc_text.find(keyword, index)
                if index == -1:
                    break
                cursor = text_edit.textCursor()
                cursor.setPosition(index)
                cursor.movePosition(
                    QTextCursor.Right, QTextCursor.KeepAnchor, len(keyword)
                )
                fmt = format_green if keyword in RISK_KEYWORDS_GREEN else format_red
                cursor.mergeCharFormat(fmt)
                index += len(keyword)
    except Exception as e:
        logger.error("Error in highlighting text: %s", e)


def fetch_email_data(
    email_address, db_path, get_hibp_api_key, result_text, submit_button
):
    submit_button.setEnabled(False)
    submit_button.setText("Searching...")
    result_text.clear()
    result_text.setPlainText("Starting email analysis...")
    try:
        api_key = get_hibp_api_key()
        if not api_key:
            result_text.setPlainText(
                "Error: HIBP API key not configured. "
                "Please set it in API Settings."
            )
            submit_button.setEnabled(True)
            submit_button.setText("Search")
            return
        result = fetch_hibp_data_synchronous(email_address, api_key)
        result_text.setPlainText(result)
        highlight_headers(result_text)
    except Exception as e:
        logger.error("Error in fetch_email_data: %s", e)
        result_text.setPlainText(f"Error during analysis: {e}")
    finally:
        submit_button.setEnabled(True)
        submit_button.setText("Search")


def open_email_lookup_window(parent, db_path):
    global EMAIL_LOOKUP_WINDOW
    if EMAIL_LOOKUP_WINDOW is not None:
        EMAIL_LOOKUP_WINDOW.activateWindow()
        EMAIL_LOOKUP_WINDOW.raise_()
        return

    email_window = QWidget(parent.window)
    email_window.setWindowTitle("Email Insights")
    email_window.resize(800, 700)
    email_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )
    EMAIL_LOOKUP_WINDOW = email_window

    original_close_event = email_window.closeEvent

    def custom_close_event(event):
        global EMAIL_LOOKUP_WINDOW
        EMAIL_LOOKUP_WINDOW = None
        if original_close_event:
            original_close_event(event)

    email_window.closeEvent = custom_close_event

    main_layout = QVBoxLayout(email_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("Email Address:")
    input_label.setFont(QFont("Arial", 12))
    input_layout.addWidget(input_label)

    email_entry = QLineEdit()
    email_entry.setFont(QFont("Arial", 10))
    email_entry.setPlaceholderText("e.g., user@example.com")
    email_entry.setMinimumWidth(300)
    input_layout.addWidget(email_entry)

    submit_button = QPushButton("Search")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    input_layout.addWidget(submit_button)

    main_layout.addLayout(input_layout)

    results_label = QLabel("Analysis Results:")
    results_label.setFont(QFont("Arial", 12))
    main_layout.addWidget(results_label)

    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
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

    def get_hibp_api_key():
        key = get_api_key("HIBP_API_KEY")
        if key is None:
            logger.warning("HIBP API key not found in api.yaml")
        return key

    def on_submit():
        email_address = email_entry.text().strip()
        if not email_address:
            QMessageBox.warning(
                email_window, "Warning", "Please enter an email address."
            )
            return
        if "@" not in email_address:
            QMessageBox.warning(
                email_window,
                "Warning",
                "Please enter a valid email address.",
            )
            return
        hibp_key = get_hibp_api_key()
        if not hibp_key:
            QMessageBox.warning(
                email_window,
                "Missing API Key",
                "HIBP API key not configured.\n\n"
                "Please configure it in API Settings:\n"
                "1. Click 'API Settings' button\n"
                "2. Enter your HIBP API key\n"
                "3. Click 'Update'",
            )
            return
        fetch_email_data(
            email_address,
            db_path,
            get_hibp_api_key,
            result_text,
            submit_button,
        )

    submit_button.clicked.connect(on_submit)
    email_entry.returnPressed.connect(on_submit)
    close_button.clicked.connect(email_window.close)
    email_window.show()
    return email_window
