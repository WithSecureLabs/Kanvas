from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
import requests
import whois
from datetime import datetime
from urllib.parse import urlparse
from functools import lru_cache
import concurrent.futures
import logging
import socket
import webbrowser
import sqlite3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

_active_domain_window = None
_FORMAT_ORANGE_HEADER = QTextCharFormat()
_FORMAT_ORANGE_HEADER.setBackground(QColor(255, 165, 0))
_FORMAT_ORANGE_HEADER.setForeground(QColor(255, 255, 255))
_FORMAT_ORANGE_HEADER.setFont(QFont("Arial", 10, QFont.Bold))
_FORMAT_RED_TEXT = QTextCharFormat()
_FORMAT_RED_TEXT.setBackground(QColor(255, 0, 0))
_FORMAT_RED_TEXT.setForeground(QColor(255, 255, 255))
_FORMAT_RED_TEXT.setFont(QFont("Arial", 10, QFont.Bold))
_FORMAT_NORMAL = QTextCharFormat()
_FORMAT_NORMAL.setFont(QFont("Arial", 10))

def open_domain_lookup_window(parent_window, db_path):
    global _active_domain_window
    if _active_domain_window is not None:
        if _active_domain_window.isVisible():
            _active_domain_window.raise_()
            _active_domain_window.activateWindow()
            return _active_domain_window
        else:
            _active_domain_window = None
    domain_window = QWidget(parent_window)  
    domain_window.setWindowTitle("Domain Lookup")
    domain_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
    _active_domain_window = domain_window
    original_close_event = domain_window.closeEvent
    def custom_close_event(event):
        global _active_domain_window
        _active_domain_window = None
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
    input_label = QLabel("Enter Domain or URL:")
    input_label.setFont(QFont("Arial", 12))
    main_layout.addWidget(input_label)
    domain_entry = QLineEdit()
    domain_entry.setFont(QFont("Arial", 10))
    domain_entry.setMinimumWidth(500)
    main_layout.addWidget(domain_entry)
    buttons_layout = QHBoxLayout()
    button_names = ["VT", "OTX", "Talos", "Criminal-IP", "Pulsedive", "Shodan"]
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
        "VT": "https://www.virustotal.com/gui/domain/{domain}",
        "OTX": "https://otx.alienvault.com/indicator/domain/{domain}",
        "Talos": "https://talosintelligence.com/reputation_center/lookup?search={domain}",
        "Criminal-IP": "https://www.criminalip.io/asset/search?query={domain}",
        "Shodan": "https://www.shodan.io/search?query={domain}",
        "Pulsedive": "https://pulsedive.com/indicator/{domain}"
    }
    def create_button_click_handler(url_template):
        def button_click_handler():
            domain_input = domain_entry.text().strip()
            if not domain_input:
                QMessageBox.warning(domain_window, "Warning", "Please enter a domain or URL.")
                return
            try:
                if not domain_input.startswith(('http://', 'https://')):
                    domain_input = 'http://' + domain_input
                parsed_url = urlparse(domain_input)
                domain = parsed_url.netloc if parsed_url.netloc else domain_input
                if domain.startswith('www.'):
                    domain = domain[4:]
                url = url_template.format(domain=domain)
                webbrowser.open(url)
            except Exception as e:
                logger.error(f"Error opening external URL for domain {domain_input}: {str(e)}")
                QMessageBox.warning(domain_window, "Error", f"Could not parse domain: {str(e)}")
        return button_click_handler
    for name in button_names:
        button = QPushButton(name)
        button.setStyleSheet(button_style)
        button.clicked.connect(create_button_click_handler(url_templates[name]))
        buttons_layout.addWidget(button)
    main_layout.addLayout(buttons_layout)
    results_label = QLabel("Results:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 10, 0, 5)
    main_layout.addWidget(results_label)
    result_text = QTextEdit()
    result_text.setFont(QFont("Arial", 10))
    result_text.setReadOnly(True)
    result_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    main_layout.addWidget(result_text, 1)  
    button_layout = QHBoxLayout()
    button_layout.setContentsMargins(0, 10, 0, 0)
    submit_button = QPushButton("Submit")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet("background-color: #4CAF50; color: white;")
    button_layout.addStretch()
    button_layout.addWidget(submit_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)
    
    @lru_cache(maxsize=8) 
    def get_vt_api_key():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT VT_API_KEY FROM user_settings WHERE id = 1")
            result = cursor.fetchone()
            conn.close()
            api_key = result[0] if result and result[0] else ""
            if api_key:
                logger.info("VirusTotal API key retrieved successfully")
            else:
                logger.warning("VirusTotal API key not found in database")
            return api_key
        except Exception as e:
            logger.error(f"Error fetching VT API key: {e}")
            return ""
    
    def apply_text_formatting(result_text_widget, text):
        result_text_widget.clear()
        format_keyword_highlight = QTextCharFormat()
        format_keyword_highlight.setBackground(QColor(255, 0, 0))  
        format_keyword_highlight.setForeground(QColor(255, 255, 255))  
        format_keyword_highlight.setFont(QFont("Arial", 10, QFont.Bold))
        cursor = result_text_widget.textCursor()
        lines = text.split('\n')
        cursor.beginEditBlock()  
        highlight_keywords = ["Malicious", "Categories", "Associated IPs"]
        for i, line in enumerate(lines):
            if i > 0:
                cursor.insertText('\n')
            if line == "=== WHOIS Information ===" or line.startswith("=== VirusTotal Results for Domain:"):
                cursor.insertText(line, _FORMAT_ORANGE_HEADER)
            elif line.startswith("Days Since Creation:"):
                parts = line.split(":", 1)
                cursor.insertText("Days Since Creation:", _FORMAT_RED_TEXT)
                if len(parts) > 1:
                    cursor.insertText(f":{parts[1]}", _FORMAT_NORMAL)
            else:
                keyword_match = False
                for keyword in highlight_keywords:
                    if keyword in line and line.strip() == keyword + ":" or line.strip().startswith(keyword + ":"):
                        keyword_pos = line.find(keyword)
                        prefix = line[:keyword_pos]
                        suffix = line[keyword_pos + len(keyword):]
                        if prefix:
                            cursor.insertText(prefix, _FORMAT_NORMAL)
                        cursor.insertText(keyword, format_keyword_highlight)
                        if suffix:
                            cursor.insertText(suffix, _FORMAT_NORMAL)
                        keyword_match = True
                        break
                if not keyword_match:
                    cursor.insertText(line, _FORMAT_NORMAL)
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
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json().get("data", {}).get("attributes", {})
                vt_results.append(vt_header)
                vt_results.append(f"Reputation: {data.get('reputation', 'N/A')}")
                vt_results.append(f"Last Analysis Date: {data.get('last_analysis_date', 'N/A')}")
                vt_results.append("\nLast Analysis Stats:")
                stats = data.get("last_analysis_stats", {})
                for key in ["harmless", "malicious", "suspicious", "undetected", "timeout"]:
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
                vt_results.append(f"{vt_header}\nError: Resource not found for domain: {domain}")
            else:
                msg = response.json().get("error", {}).get("message", "No error message provided")
                vt_results.append(f"{vt_header}\nError: VirusTotal API request failed ({response.status_code}): {msg}")
        except Exception as e:
            logger.error(f"Exception during VirusTotal API request for {domain}: {str(e)}")
            vt_results.append(f"{vt_header}\nError: {e}")
        return vt_results
    
    def fetch_whois_data(domain):
        whois_results = []
        whois_header = "=== WHOIS Information ==="
        try:
            socket.setdefaulttimeout(15)
            whois_results.append("\n" + whois_header)
            whois_data = whois.whois(domain)
            creation_date = whois_data.creation_date
            if isinstance(creation_date, list) and creation_date:
                creation_date = creation_date[0]
            if creation_date:
                current_date = datetime.now()
                if hasattr(creation_date, 'replace'):
                    creation_date = creation_date.replace(tzinfo=None)
                days_since_creation = (current_date - creation_date).days
                whois_results.append(f"Domain: {domain}")
                whois_results.append(f"Registrar: {whois_data.registrar or 'N/A'}")
                whois_results.append(f"Creation Date: {creation_date}")
                expiration_date = whois_data.expiration_date
                if isinstance(expiration_date, list) and expiration_date:
                    expiration_date = expiration_date[0]
                whois_results.append(f"Expiration Date: {expiration_date or 'N/A'}")
                whois_results.append(f"Days Since Creation: {days_since_creation} days")
                if whois_data.name_servers:
                    name_servers = whois_data.name_servers
                    if isinstance(name_servers, list):
                        name_servers = ', '.join(name_servers[:3])  
                    whois_results.append(f"Name Servers: {name_servers}")
                if whois_data.status:
                    status = whois_data.status
                    if isinstance(status, list):
                        status = ', '.join(status[:2])  
                    whois_results.append(f"Status: {status}")
            else:
                whois_results.append("Creation Date: Not available")
                whois_results.append(f"Domain: {domain}")
                whois_results.append(f"Registrar: {whois_data.registrar or 'N/A'}")
        except Exception as e:
            logger.error(f"Error fetching WHOIS data for {domain}: {str(e)}")
            whois_results.append(f"Error fetching WHOIS data: {e}")
        finally:
            socket.setdefaulttimeout(None)
        return whois_results
    
    def fetch_domain_info():
        submit_button.setText("Searching...")
        submit_button.setEnabled(False)
        domain_entry.setEnabled(False)
        QApplication.processEvents()  
        domain_or_url = domain_entry.text().strip()
        if not domain_or_url:
            QMessageBox.warning(domain_window, "Warning", "Please enter a domain or URL.")
            submit_button.setText("Submit")
            submit_button.setEnabled(True)
            domain_entry.setEnabled(True)
            return
        result_text.clear()
        try:
            if not domain_or_url.startswith(('http://', 'https://')):
                domain_or_url = 'http://' + domain_or_url
            parsed_url = urlparse(domain_or_url)
            domain = parsed_url.netloc if parsed_url.netloc else domain_or_url
            if domain.startswith('www.'):
                domain = domain[4:]
        except Exception as e:
            logger.error(f"Error parsing URL {domain_or_url}: {str(e)}")
            result_text.setText(f"Error parsing URL: {e}")
            submit_button.setText("Submit")
            submit_button.setEnabled(True)
            domain_entry.setEnabled(True)
            return
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            vt_api_key = get_vt_api_key()
            vt_future = executor.submit(fetch_virustotal_data, domain, vt_api_key)
            whois_future = executor.submit(fetch_whois_data, domain)
            vt_results = vt_future.result()
            all_results.extend(vt_results)
            whois_results = whois_future.result()
            all_results.extend(whois_results)
        full_text = "\n".join(all_results)
        apply_text_formatting(result_text, full_text)
        submit_button.setText("Submit")
        submit_button.setEnabled(True)
        domain_entry.setEnabled(True)
    submit_button.clicked.connect(fetch_domain_info)
    domain_entry.returnPressed.connect(fetch_domain_info)  
    domain_window.show()
    return domain_window