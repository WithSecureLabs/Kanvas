# IP Lookup window for Kanvas: look up IP addresses via TOR database, IP-API, Shodan,
# and VirusTotal; display geolocation, threat assessment, and provide quick links.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import sqlite3
import webbrowser
from datetime import datetime

import requests
import shodan
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

IP_API_URL = "http://ip-api.com/json"
VT_IP_API = "https://www.virustotal.com/api/v3/ip_addresses"
VT_COMMENTS_LIMIT = 10
REQUEST_TIMEOUT = 10
VT_REQUEST_TIMEOUT = 15
MAX_DNS_RECORDS = 10
DETECTION_RATE_HIGH = 15
DETECTION_RATE_MEDIUM = 5

TOR_HEADER = "=== Details found on TOR DB ===\n"
IP_API_HEADER = "\n=== IP-API Data === \n"
SHODAN_HEADER = "\n=== Shodan Data ===\n"
VT_HEADER = "\n=== VirusTotal Data ===\n"
VT_COMMENTS_HEADER = "\n=== VirusTotal Comments for the IP Address ===\n"

HEADER_PATTERNS = [
    "=== VirusTotal Data ===",
    "=== Shodan Data ===",
    "=== IP-API Data ===",
    "=== Details found on TOR DB ===",
    "=== VirusTotal Comments for the IP Address ===",
]
RED_HIGHLIGHT_KEYWORDS = [
    "Vulnerabilities:",
    "Open Ports and Services:",
    "Malicious:",
]

IP_BUTTON_NAMES = [
    "VT",
    "OTX",
    "DSheild",
    "Talos",
    "Spamhaus",
    "Criminal-IP",
    "Shoden",
    "AbuseIPDB",
    "Pulsedive",
]
IP_URL_TEMPLATES = {
    "VT": "https://www.virustotal.com/gui/ip-address/{ip}",
    "OTX": "https://otx.alienvault.com/indicator/ip/{ip}",
    "DSheild": "https://www.dshield.org/ipinfo/{ip}",
    "Talos": "https://talosintelligence.com/reputation_center/lookup?search={ip}",
    "Spamhaus": "https://check.spamhaus.org/results/?query={ip}",
    "Criminal-IP": "https://www.criminalip.io/asset/report/{ip}",
    "Shoden": "https://www.shodan.io/host/{ip}",
    "AbuseIPDB": "https://www.abuseipdb.com/check/{ip}",
    "Pulsedive": "https://pulsedive.com/indicator/{ip}",
}

IP_LOOKUP_WINDOW = None


def fetch_tor_data(ip_address, db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ipaddress_ FROM tor_list WHERE ipaddress_ = ?",
            (ip_address,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return [
                TOR_HEADER,
                f"■ {ip_address} found on TOR database",
                "■ This IP address is associated with TOR exit nodes",
                "■ Potential for anonymous traffic\n",
            ]
        return [
            TOR_HEADER,
            f"■ {ip_address} NOT found on TOR database",
            "■ No association with known TOR exit nodes\n",
        ]
    except sqlite3.Error as e:
        logger.error("TOR database error: %s", e)
        return [TOR_HEADER, f"Database error: {e}\n"]


def fetch_ip_api_data(ip_address):
    try:
        response = requests.get(
            f"{IP_API_URL}/{ip_address}", timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            logger.error("IP-API HTTP error: %s", response.status_code)
            return [
                IP_API_HEADER,
                f"Error: Unable to fetch data (HTTP {response.status_code})",
            ]
        data = response.json()
        if data.get("status") != "success":
            logger.warning(
                "IP-API lookup failed: %s",
                data.get("message", "Unknown error"),
            )
            return [
                IP_API_HEADER,
                f"Error: {data.get('message', 'Unknown error')}",
            ]
        return [
            IP_API_HEADER,
            f"► IP: {data['query']}",
            f"► Country: {data['country']} ({data.get('countryCode', 'N/A')})",
            f"► Region: {data['regionName']} ({data.get('region', 'N/A')})",
            f"► City: {data['city']}",
            f"► ISP: {data['isp']}",
            f"► Organization: {data.get('org', 'N/A')}",
            f"► AS: {data.get('as', 'N/A')}",
        ]
    except requests.RequestException as e:
        logger.error("IP-API connection error: %s", e)
        return [IP_API_HEADER, f"Error: Connection error: {e}"]
    except Exception as e:
        logger.error("IP-API unexpected error: %s", e)
        return [IP_API_HEADER, f"Error: {e}"]


def fetch_shodan_data(ip_address, get_shodan_api_key):
    api_key = get_shodan_api_key()
    if not api_key:
        return [SHODAN_HEADER, "Error: Shodan API key not available"]
    try:
        api = shodan.Shodan(api_key)
        host = api.host(ip_address)
        result = [
            SHODAN_HEADER,
            f"► IP: {host['ip_str']}",
            f"► Organization: {host.get('org', 'N/A')}",
            f"► ISP: {host.get('isp', 'N/A')}",
            f"► Location: {host.get('city', 'N/A')}, {host.get('country_name', 'N/A')}",
            f"► Coordinates: {host.get('latitude', 'N/A')}, {host.get('longitude', 'N/A')}",
            f"► Hostnames: {', '.join(host.get('hostnames', [])) or 'None'}",
            f"► Domains: {', '.join(host.get('domains', [])) or 'None'}",
            f"► Operating System: {host.get('os', 'N/A')}",
            f"► Last Update: {host.get('last_update', 'N/A')}",
            "\nVulnerabilities:",
        ]
        vulns = host.get("vulns", [])
        if vulns:
            for vuln in vulns:
                result.append(f"  • CVE: {vuln}")
        else:
            result.append("  • No vulnerabilities found.")
        result.append("\nOpen Ports and Services:")
        for item in host.get("data", []):
            result.append(
                f"  • Port: {item['port']} ({item['transport'].upper()})"
            )
            result.append(f"    Service: {item.get('product', 'N/A')}")
        return result
    except shodan.APIError as e:
        logger.error("Shodan API error: %s", e)
        return [SHODAN_HEADER, f"Error: Shodan API Error: {e}"]
    except Exception as e:
        logger.error("Shodan unexpected error: %s", e)
        return [SHODAN_HEADER, "Error: Unexpected Error: {e}"]


def fetch_vt_data(ip_address, get_vt_api_key):
    api_key = get_vt_api_key()
    if not api_key:
        logger.warning("VirusTotal API key not available")
        return [VT_HEADER, "Error: VirusTotal API key not available"]
    try:
        url = f"{VT_IP_API}/{ip_address}"
        headers = {"x-apikey": api_key}
        response = requests.get(
            url, headers=headers, timeout=VT_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            logger.error(
                "VirusTotal API request failed with status code %s",
                response.status_code,
            )
            return [
                VT_HEADER,
                f"Error: VirusTotal API request failed with "
                f"status code {response.status_code}",
            ]
        data = response.json().get("data", {}).get("attributes", {})
        logger.info("VirusTotal lookup successful")
        result = [
            VT_HEADER,
            f"► IP Address: {ip_address}",
            f"► Country: {data.get('country', 'N/A')}",
            f"► AS Owner: {data.get('as_owner', 'N/A')}",
            f"► ASN: {data.get('asn', 'N/A')}",
            f"► Network: {data.get('network', 'N/A')}",
            f"► Continent: {data.get('continent', 'N/A')}",
            f"► Reputation: {data.get('reputation', 'N/A')}",
            "\nLast Analysis Stats:",
        ]
        analysis_stats = data.get("last_analysis_stats", {})
        harmless = analysis_stats.get("harmless", 0)
        malicious = analysis_stats.get("malicious", 0)
        suspicious = analysis_stats.get("suspicious", 0)
        result.append(f"  • Harmless: {harmless}")
        result.append(f"  • Malicious: {malicious}")
        result.append(f"  • Suspicious: {suspicious}")
        result.append(f"  • Undetected: {analysis_stats.get('undetected', 0)}")
        result.append(f"  • Timeout: {analysis_stats.get('timeout', 0)}")
        logger.info(
            "VT Analysis - Malicious: %s, Suspicious: %s, Harmless: %s",
            malicious,
            suspicious,
            harmless,
        )
        total_engines = sum(analysis_stats.values())
        if total_engines > 0:
            detection_rate = (
                (malicious + suspicious) / total_engines * 100
            )
            result.append("\nThreat Assessment:")
            if detection_rate >= DETECTION_RATE_HIGH:
                logger.warning(
                    "HIGH RISK IP detected: %s - Detection Rate: %.1f%%",
                    ip_address,
                    detection_rate,
                )
                result.append(
                    f"  ⚠ HIGH RISK - Detection Rate: {detection_rate:.1f}%"
                )
            elif detection_rate >= DETECTION_RATE_MEDIUM:
                logger.warning(
                    "MEDIUM RISK IP detected: %s - Detection Rate: %.1f%%",
                    ip_address,
                    detection_rate,
                )
                result.append(
                    f"  ⚠ MEDIUM RISK - Detection Rate: {detection_rate:.1f}%"
                )
            else:
                logger.info(
                    "LOW RISK IP: %s - Detection Rate: %.1f%%",
                    ip_address,
                    detection_rate,
                )
                result.append(
                    f"  ✓ LOW RISK - Detection Rate: {detection_rate:.1f}%"
                )
        result.append("\nAssociated Domains:")
        resolutions = data.get("last_dns_records", [])
        if resolutions:
            logger.info(
                "Found %d associated domains for %s",
                len(resolutions),
                ip_address,
            )
            for i, record in enumerate(resolutions[:MAX_DNS_RECORDS]):
                if record.get("type") == "A" and record.get("value"):
                    result.append(f"  • {record.get('value')}")
            remaining = len(resolutions) - MAX_DNS_RECORDS
            if remaining > 0:
                result.append(f"  • ... and {remaining} more domains")
        else:
            result.append("  • No associated domains found.")
        try:
            comments_url = (
                f"{VT_IP_API}/{ip_address}/comments"
                f"?limit={VT_COMMENTS_LIMIT}"
            )
            comments_headers = {
                "accept": "application/json",
                "x-apikey": api_key,
            }
            comments_response = requests.get(
                comments_url,
                headers=comments_headers,
                timeout=REQUEST_TIMEOUT,
            )
            comments_data = comments_response.json()
            comments = comments_data.get("data", [])
            comments_result = [VT_COMMENTS_HEADER]
            if not comments:
                logger.info(
                    "No VirusTotal comments found for %s", ip_address
                )
                comments_result.append("No comments found.")
            else:
                for idx, comment in enumerate(comments, 1):
                    attr = comment.get("attributes", {})
                    text = attr.get("text", "")
                    tags = attr.get("tags", [])
                    votes = attr.get("votes", {})
                    date = attr.get("date")
                    date_str = None
                    if date:
                        date_str = datetime.utcfromtimestamp(date).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    comments_result.append(f"▼ Comment {idx}:")
                    comments_result.append(f"  • Text: {text}")
                    if tags:
                        comments_result.append(
                            f"  • Tags: {', '.join(tags)}"
                        )
                    if votes:
                        comments_result.append(
                            f"  • Votes: +{votes.get('positive', 0)}/-{votes.get('negative', 0)}"
                        )
                    comments_result.append(f"  • Date: {date_str}")
                    if idx < len(comments):
                        comments_result.append("  " + "—" * 30)
            result.extend(comments_result)
        except Exception as e:
            logger.error(
                "Error fetching VirusTotal comments: %s", e
            )
            result.append(f"Error fetching VirusTotal comments: {e}")
        return result
    except requests.RequestException as e:
        logger.error("VirusTotal connection error: %s", e)
        return [VT_HEADER, f"Error: Connection error: {e}"]
    except Exception as e:
        logger.error("VirusTotal unexpected error: %s", e)
        return [VT_HEADER, f"Error: {e}"]


def fetch_ip_data_synchronous(
    ip_address, db_path, get_shodan_api_key, get_vt_api_key
):
    try:
        logger.info("Starting IP lookup")
        tor_result = fetch_tor_data(ip_address, db_path)
        ip_api_result = fetch_ip_api_data(ip_address)
        shodan_result = fetch_shodan_data(ip_address, get_shodan_api_key)
        vt_result = fetch_vt_data(ip_address, get_vt_api_key)
        combined = "\n".join(
            tor_result + shodan_result + ip_api_result + vt_result
        )
        return combined
    except Exception as e:
        logger.error(
            "Unexpected error during IP lookup for %s: %s",
            ip_address,
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
        for keyword in RED_HIGHLIGHT_KEYWORDS:
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
                cursor.mergeCharFormat(format_red)
                index += len(keyword)
    except Exception as e:
        logger.error("Error in highlighting text: %s", e)


def fetch_ip_location(
    ip_address, db_path, get_shodan_api_key, get_vt_api_key,
    result_text, submit_button
):
    submit_button.setEnabled(False)
    submit_button.setText("Searching...")
    result_text.clear()
    result_text.setPlainText("Starting search...")
    try:
        result = fetch_ip_data_synchronous(
            ip_address, db_path, get_shodan_api_key, get_vt_api_key
        )
        result_text.setPlainText(result)
        highlight_headers(result_text)
    except Exception as e:
        logger.error("Error in fetch_ip_location: %s", e)
        result_text.setPlainText(f"Error during lookup: {e}")
    finally:
        submit_button.setEnabled(True)
        submit_button.setText("Search")


def open_ip_lookup_window(parent, db_path):
    global IP_LOOKUP_WINDOW
    if IP_LOOKUP_WINDOW is not None:
        IP_LOOKUP_WINDOW.activateWindow()
        IP_LOOKUP_WINDOW.raise_()
        return IP_LOOKUP_WINDOW

    ip_window = QWidget(parent.window)
    ip_window.setWindowTitle("IP Lookup")
    ip_window.resize(720, 600)
    ip_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )
    IP_LOOKUP_WINDOW = ip_window

    original_close_event = ip_window.closeEvent

    def custom_close_event(event):
        global IP_LOOKUP_WINDOW
        IP_LOOKUP_WINDOW = None
        if original_close_event:
            original_close_event(event)

    ip_window.closeEvent = custom_close_event

    main_layout = QVBoxLayout(ip_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("IP Address:")
    input_label.setFont(QFont("Arial", 12))
    input_layout.addWidget(input_label)

    ip_entry = QLineEdit()
    ip_entry.setFont(QFont("Arial", 10))
    ip_entry.setPlaceholderText("e.g., 8.8.8.8")
    ip_entry.setMinimumWidth(300)
    input_layout.addWidget(ip_entry)

    submit_button = QPushButton("Search")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet(styles.BUTTON_STYLE_BASE)
    input_layout.addWidget(submit_button)

    main_layout.addLayout(input_layout)

    buttons_layout = QHBoxLayout()
    for name in IP_BUTTON_NAMES:
        button = QPushButton(name)
        button.setStyleSheet(styles.BUTTON_STYLE_PINK)

        def make_handler(url_template):
            def handler():
                ip = ip_entry.text().strip()
                if not ip:
                    QMessageBox.warning(
                        ip_window,
                        "Warning",
                        "Please enter an IP address first.",
                    )
                    return
                url = url_template.format(ip=ip)
                webbrowser.open(url)

            return handler

        button.clicked.connect(make_handler(IP_URL_TEMPLATES[name]))
        buttons_layout.addWidget(button)

    main_layout.addLayout(buttons_layout)

    results_label = QLabel("Result:")
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

    def get_shodan_api_key():
        return get_api_key("SHODEN_API_KEY")

    def get_vt_api_key():
        return get_api_key("VT_API_KEY")

    def on_submit():
        ip_address = ip_entry.text().strip()
        if not ip_address:
            QMessageBox.warning(
                ip_window, "Warning", "Please enter an IP address."
            )
            return
        shodan_key = get_shodan_api_key()
        vt_key = get_vt_api_key()
        missing_keys = []
        if not shodan_key:
            missing_keys.append("Shodan")
        if not vt_key:
            missing_keys.append("VirusTotal")
        if missing_keys:
            QMessageBox.warning(
                ip_window,
                "Missing API Keys",
                f"The following API keys are not configured: "
                f"{', '.join(missing_keys)}.\n\n"
                "Some information will not be available in the results.",
            )
        fetch_ip_location(
            ip_address,
            db_path,
            get_shodan_api_key,
            get_vt_api_key,
            result_text,
            submit_button,
        )

    submit_button.clicked.connect(on_submit)
    ip_entry.returnPressed.connect(on_submit)
    close_button.clicked.connect(ip_window.close)
    ip_window.show()
    return ip_window
