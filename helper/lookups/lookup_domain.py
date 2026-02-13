# Domain Lookup window for Kanvas: fetch WHOIS and VirusTotal data for domains/URLs,
# display formatted results, and provide quick links to VT, OTX, Talos, Criminal-IP, etc.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import socket
import webbrowser
from datetime import datetime
from urllib.parse import urlparse

import requests
import whois
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

REQUEST_TIMEOUT = 10
WHOIS_TIMEOUT = 15

DOMAIN_BUTTON_NAMES = [
    "VT",
    "OTX",
    "Talos",
    "Criminal-IP",
    "Pulsedive",
    "Shodan",
]
DOMAIN_URL_TEMPLATES = {
    "VT": "https://www.virustotal.com/gui/domain/{domain}",
    "OTX": "https://otx.alienvault.com/indicator/domain/{domain}",
    "Talos": "https://talosintelligence.com/reputation_center/lookup?search={domain}",
    "Criminal-IP": "https://www.criminalip.io/asset/search?query={domain}",
    "Shodan": "https://www.shodan.io/search?query={domain}",
    "Pulsedive": "https://pulsedive.com/indicator/{domain}",
}
HIGHLIGHT_KEYWORDS = ["Malicious", "Categories", "Associated IPs"]

active_domain_window = None

FORMAT_ORANGE_HEADER = QTextCharFormat()
FORMAT_ORANGE_HEADER.setBackground(QColor(styles.HEADER_HIGHLIGHT_BG))
FORMAT_ORANGE_HEADER.setForeground(QColor(styles.HEADER_HIGHLIGHT_FG))
FORMAT_ORANGE_HEADER.setFont(QFont("Arial", 10, QFont.Bold))
FORMAT_RED_TEXT = QTextCharFormat()
FORMAT_RED_TEXT.setBackground(QColor(styles.KEYWORD_HIGHLIGHT_BG))
FORMAT_RED_TEXT.setForeground(QColor(styles.KEYWORD_HIGHLIGHT_FG))
FORMAT_RED_TEXT.setFont(QFont("Arial", 10, QFont.Bold))
FORMAT_NORMAL = QTextCharFormat()
FORMAT_NORMAL.setFont(QFont("Arial", 10))


def extract_domain(domain_or_url):
    if not domain_or_url.strip():
        return None
    s = domain_or_url.strip()
    if not s.startswith(("http://", "https://")):
        s = "http://" + s
    parsed = urlparse(s)
    domain = parsed.netloc or s
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def apply_text_formatting(result_text_widget, text):
    result_text_widget.clear()
    format_keyword = QTextCharFormat()
    format_keyword.setBackground(QColor(styles.KEYWORD_HIGHLIGHT_BG))
    format_keyword.setForeground(QColor(styles.KEYWORD_HIGHLIGHT_FG))
    format_keyword.setFont(QFont("Arial", 10, QFont.Bold))
    cursor = result_text_widget.textCursor()
    lines = text.split("\n")
    cursor.beginEditBlock()
    for i, line in enumerate(lines):
        if i > 0:
            cursor.insertText("\n")
        if line == "=== WHOIS Information ===" or line.startswith(
            "=== VirusTotal Results for Domain:"
        ):
            cursor.insertText(line, FORMAT_ORANGE_HEADER)
        elif line.startswith("Days Since Creation:"):
            parts = line.split(":", 1)
            cursor.insertText("Days Since Creation:", FORMAT_RED_TEXT)
            if len(parts) > 1:
                cursor.insertText(f":{parts[1]}", FORMAT_NORMAL)
        else:
            keyword_match = False
            for keyword in HIGHLIGHT_KEYWORDS:
                if (keyword in line and line.strip() == keyword + ":") or (
                    line.strip().startswith(keyword + ":")
                ):
                    keyword_pos = line.find(keyword)
                    prefix = line[:keyword_pos]
                    suffix = line[keyword_pos + len(keyword) :]
                    if prefix:
                        cursor.insertText(prefix, FORMAT_NORMAL)
                    cursor.insertText(keyword, format_keyword)
                    if suffix:
                        cursor.insertText(suffix, FORMAT_NORMAL)
                    keyword_match = True
                    break
            if not keyword_match:
                cursor.insertText(line, FORMAT_NORMAL)
    cursor.endEditBlock()
    cursor.movePosition(QTextCursor.Start)
    result_text_widget.setTextCursor(cursor)


def fetch_virustotal_data(domain, api_key):
    vt_results = []
    vt_header = f"=== VirusTotal Results for Domain: {domain} ==="
    if not api_key:
        return ["VirusTotal API key not configured."]
    try:
        url = f"https://www.virustotal.com/api/v3/domains/{domain}"
        headers = {"x-apikey": api_key}
        response = requests.get(
            url, headers=headers, timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            data = response.json().get("data", {}).get("attributes", {})
            vt_results.append(vt_header)
            vt_results.append(f"Reputation: {data.get('reputation', 'N/A')}")
            vt_results.append(
                f"Last Analysis Date: {data.get('last_analysis_date', 'N/A')}"
            )
            vt_results.append("\nLast Analysis Stats:")
            stats = data.get("last_analysis_stats", {})
            for key in [
                "harmless",
                "malicious",
                "suspicious",
                "undetected",
                "timeout",
            ]:
                vt_results.append(f"  {key.capitalize()}: {stats.get(key, 0)}")
            vt_results.append("\nCategories:")
            for category, desc in data.get("categories", {}).items():
                vt_results.append(f"  {category}: {desc}")
            vt_results.append("\nAssociated IPs:")
            resolutions = data.get("last_dns_records", [])
            found_ip = False
            for record in resolutions:
                if record.get("type") == "A" and record.get("value"):
                    vt_results.append(f"  {record.get('value')}")
                    found_ip = True
            if not found_ip:
                vt_results.append("  No associated IPs found.")
        elif response.status_code == 404:
            vt_results.append(
                f"{vt_header}\nError: Resource not found for domain: {domain}"
            )
        else:
            msg = response.json().get("error", {}).get(
                "message", "No error message provided"
            )
            vt_results.append(
                f"{vt_header}\nError: VirusTotal API request failed "
                f"({response.status_code}): {msg}"
            )
    except Exception as e:
        logger.error(
            "Exception during VirusTotal API request for %s: %s",
            domain,
            str(e),
        )
        vt_results.append(f"{vt_header}\nError: {e}")
    return vt_results


def fetch_whois_data(domain):
    whois_results = []
    whois_header = "=== WHOIS Information ==="
    try:
        socket.setdefaulttimeout(WHOIS_TIMEOUT)
        whois_results.append("\n" + whois_header)
        whois_data = whois.whois(domain)
        creation_date = whois_data.creation_date
        if isinstance(creation_date, list) and creation_date:
            creation_date = creation_date[0]
        if creation_date:
            current_date = datetime.now()
            if hasattr(creation_date, "replace"):
                creation_date = creation_date.replace(tzinfo=None)
            days_since_creation = (current_date - creation_date).days
            whois_results.append(f"Domain: {domain}")
            whois_results.append(
                f"Registrar: {whois_data.registrar or 'N/A'}"
            )
            whois_results.append(f"Creation Date: {creation_date}")
            expiration_date = whois_data.expiration_date
            if isinstance(expiration_date, list) and expiration_date:
                expiration_date = expiration_date[0]
            whois_results.append(
                f"Expiration Date: {expiration_date or 'N/A'}"
            )
            whois_results.append(
                f"Days Since Creation: {days_since_creation} days"
            )
            if whois_data.name_servers:
                name_servers = whois_data.name_servers
                if isinstance(name_servers, list):
                    name_servers = ", ".join(name_servers[:3])
                whois_results.append(f"Name Servers: {name_servers}")
            if whois_data.status:
                status = whois_data.status
                if isinstance(status, list):
                    status = ", ".join(status[:2])
                whois_results.append(f"Status: {status}")
        else:
            whois_results.append("Creation Date: Not available")
            whois_results.append(f"Domain: {domain}")
            whois_results.append(
                f"Registrar: {whois_data.registrar or 'N/A'}"
            )
    except Exception as e:
        logger.error("Error fetching WHOIS data for %s: %s", domain, str(e))
        whois_results.append(f"Error fetching WHOIS data: {e}")
    finally:
        socket.setdefaulttimeout(None)
    return whois_results


def open_domain_lookup_window(parent_window, db_path):
    global active_domain_window
    if active_domain_window is not None:
        if active_domain_window.isVisible():
            active_domain_window.raise_()
            active_domain_window.activateWindow()
            return active_domain_window
        active_domain_window = None

    domain_window = QWidget(parent_window.window)
    domain_window.setWindowTitle("Domain Lookup")
    domain_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )
    active_domain_window = domain_window

    original_close_event = domain_window.closeEvent

    def custom_close_event(event):
        global active_domain_window
        active_domain_window = None
        if original_close_event:
            original_close_event(event)
        event.accept()

    domain_window.closeEvent = custom_close_event

    base_width = 600
    base_height = 500
    window_width = int(base_width * 1.2)
    window_height = int(base_height * 1.2)
    domain_window.resize(window_width, window_height)
    domain_window.setFixedSize(window_width, window_height)

    main_layout = QVBoxLayout(domain_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("Domain or URL:")
    input_label.setFont(QFont("Arial", 12))
    input_layout.addWidget(input_label)

    domain_entry = QLineEdit()
    domain_entry.setFont(QFont("Arial", 10))
    domain_entry.setMinimumWidth(300)
    input_layout.addWidget(domain_entry)

    submit_button = QPushButton("Search")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    input_layout.addWidget(submit_button)

    main_layout.addLayout(input_layout)

    buttons_layout = QHBoxLayout()
    for name in DOMAIN_BUTTON_NAMES:
        button = QPushButton(name)
        button.setStyleSheet(styles.BUTTON_STYLE_PINK)

        def make_handler(url_template):
            def handler():
                domain_input = domain_entry.text().strip()
                if not domain_input:
                    QMessageBox.warning(
                        domain_window,
                        "Warning",
                        "Please enter a domain or URL.",
                    )
                    return
                domain = extract_domain(domain_input)
                if not domain:
                    QMessageBox.warning(
                        domain_window,
                        "Warning",
                        "Please enter a domain or URL.",
                    )
                    return
                try:
                    url = url_template.format(domain=domain)
                    webbrowser.open(url)
                except Exception as e:
                    logger.error(
                        "Error opening external URL for domain %s: %s",
                        domain_input,
                        str(e),
                    )
                    QMessageBox.warning(
                        domain_window,
                        "Error",
                        f"Could not parse domain: {str(e)}",
                    )

            return handler

        button.clicked.connect(
            make_handler(DOMAIN_URL_TEMPLATES[name])
        )
        buttons_layout.addWidget(button)
    main_layout.addLayout(buttons_layout)

    results_label = QLabel("Results:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 10, 0, 5)
    main_layout.addWidget(results_label)

    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
    result_text.setReadOnly(True)
    result_text.setTextInteractionFlags(
        Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
    )
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
        return key or ""

    def fetch_domain_info():
        submit_button.setText("Searching...")
        submit_button.setEnabled(False)
        domain_entry.setEnabled(False)
        domain_or_url = domain_entry.text().strip()

        if not domain_or_url:
            QMessageBox.warning(
                domain_window,
                "Warning",
                "Please enter a domain or URL.",
            )
            submit_button.setText("Search")
            submit_button.setEnabled(True)
            domain_entry.setEnabled(True)
            return

        result_text.clear()
        domain = extract_domain(domain_or_url)
        if not domain:
            logger.error("Error parsing URL %s", domain_or_url)
            result_text.setText("Error: Could not parse domain or URL.")
            submit_button.setText("Search")
            submit_button.setEnabled(True)
            domain_entry.setEnabled(True)
            return

        try:
            vt_api_key = get_vt_api_key()
            vt_results = fetch_virustotal_data(domain, vt_api_key)
            whois_results = fetch_whois_data(domain)
            full_text = "\n".join(vt_results + whois_results)
            apply_text_formatting(result_text, full_text)
        except Exception as e:
            logger.error("Error during domain lookup: %s", e)
            result_text.setText(f"Error during domain lookup: {e}")
        finally:
            submit_button.setText("Search")
            submit_button.setEnabled(True)
            domain_entry.setEnabled(True)

    submit_button.clicked.connect(fetch_domain_info)
    domain_entry.returnPressed.connect(fetch_domain_info)
    close_button.clicked.connect(domain_window.close)
    domain_window.show()
    return domain_window
