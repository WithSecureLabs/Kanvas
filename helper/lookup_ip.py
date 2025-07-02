import sqlite3
import requests
import shodan
import threading
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTextEdit, QScrollArea, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from datetime import datetime
import webbrowser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

IP_LOOKUP_WINDOW = None
class WorkerSignals(QObject):
    finished = Signal(str)
    progress = Signal(int)
    error = Signal(str)

def fetch_ip_location_threaded(ip_address, db_path, get_shodan_api_key, get_vt_api_key, signals):
    try:
        tor_result = []
        shodan_result = []
        ip_api_result = []
        vt_result = []
        signals.progress.emit(5)
        logger.info("Initial progress sent")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_header = [
            f"╔═══════════════════════════════════════════════════",
            f"║ IP LOOKUP REPORT: {ip_address}",
            f"║ Generated: {current_time}",
            f"╚═══════════════════════════════════════════════════\n"
        ]
        signals.progress.emit(10)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT ipaddress_ FROM tor_list WHERE ipaddress_ = ?", (ip_address,))
            row = cursor.fetchone()
            tor_header = "=== Detailes found on TOR DB ===\n"
            if row:
                tor_result.append(tor_header)
                tor_result.append(f"■ {ip_address} found on TOR database")
                tor_result.append(f"■ This IP address is associated with TOR exit nodes")
                tor_result.append(f"■ Potential for anonymous traffic\n")
            else:
                tor_result.append(tor_header)
                tor_result.append(f"■ {ip_address} NOT found on TOR database")
                tor_result.append(f"■ No association with known TOR exit nodes\n")
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"TOR database error: {e}")
            tor_result = [f"=== Detailes found on TOR DB ===\n", f"Database error: {e}\n"]
        signals.progress.emit(25)
        try:
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    ip_api_result = [
                        "\n=== IP-API Data === \n",
                        f"► IP: {data['query']}",
                        f"► Country: {data['country']} ({data.get('countryCode', 'N/A')})",
                        f"► Region: {data['regionName']} ({data.get('region', 'N/A')})",
                        f"► City: {data['city']}",
                        f"► ISP: {data['isp']}",
                        f"► Organization: {data.get('org', 'N/A')}",
                        f"► AS: {data.get('as', 'N/A')}",
                    ]
                else:
                    logger.warning(f"IP-API lookup failed: {data.get('message', 'Unknown error')}")
                    ip_api_result = ["\n=== IP-API Data === \n", f"Error: {data.get('message', 'Unknown error')}"]
            else:
                logger.error(f"IP-API HTTP error: {response.status_code}")
                ip_api_result = ["\n=== IP-API Data === \n", f"Error: Unable to fetch data (HTTP {response.status_code})"]
        except requests.RequestException as e:
            logger.error(f"IP-API connection error: {e}")
            ip_api_result = ["\n=== IP-API Data === \n", f"Error: Connection error: {e}"]
        except Exception as e:
            logger.error(f"IP-API unexpected error: {e}")
            ip_api_result = ["\n=== IP-API Data === \n", f"Error: {e}"]
        signals.progress.emit(40)
        shodan_api_key = get_shodan_api_key()
        if shodan_api_key:
            try:
                api = shodan.Shodan(shodan_api_key)
                host = api.host(ip_address)
                shodan_result.append("\n=== Shodan Data ===\n")
                shodan_result.append(f"► IP: {host['ip_str']}")
                shodan_result.append(f"► Organization: {host.get('org', 'N/A')}")
                shodan_result.append(f"► ISP: {host.get('isp', 'N/A')}")
                shodan_result.append(f"► Location: {host.get('city', 'N/A')}, {host.get('country_name', 'N/A')}")
                shodan_result.append(f"► Coordinates: {host.get('latitude', 'N/A')}, {host.get('longitude', 'N/A')}")
                shodan_result.append(f"► Hostnames: {', '.join(host.get('hostnames', [])) or 'None'}")
                shodan_result.append(f"► Domains: {', '.join(host.get('domains', [])) or 'None'}")
                shodan_result.append(f"► Operating System: {host.get('os', 'N/A')}")
                shodan_result.append(f"► Last Update: {host.get('last_update', 'N/A')}")
                shodan_result.append("\nVulnerabilities:")
                vulns = host.get('vulns', [])
                if vulns:
                    for vuln in vulns:
                        shodan_result.append(f"  • CVE: {vuln}")
                else:
                    shodan_result.append("  • No vulnerabilities found.")
                shodan_result.append("\nOpen Ports and Services:")
                for item in host.get('data', []):
                    shodan_result.append(f"  • Port: {item['port']} ({item['transport'].upper()})")
                    shodan_result.append(f"    Service: {item.get('product', 'N/A')}")
            except shodan.APIError as e:
                logger.error(f"Shodan API error: {e}")
                shodan_result = [f"\n=== Shodan Data ===\n", f"Error: Shodan API Error: {e}"]
            except Exception as e:
                logger.error(f"Shodan unexpected error: {e}")
                shodan_result = [f"\n=== Shodan Data ===\n", f"Error: Unexpected Error: {e}"]
        else:
            shodan_result = ["\n=== Shodan Data ===\n", "Error: Shodan API key not available"]
        signals.progress.emit(70)
        vt_api_key = get_vt_api_key()
        if vt_api_key:
            try:
                url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip_address}"
                headers = {"x-apikey": vt_api_key}
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json().get("data", {}).get("attributes", {})
                    logger.info("VirusTotal lookup successful")
                    vt_result.append("\n=== VirusTotal Data ===\n")
                    vt_result.append(f"► IP Address: {ip_address}")
                    vt_result.append(f"► Country: {data.get('country', 'N/A')}")
                    vt_result.append(f"► AS Owner: {data.get('as_owner', 'N/A')}")
                    vt_result.append(f"► ASN: {data.get('asn', 'N/A')}")
                    vt_result.append(f"► Network: {data.get('network', 'N/A')}")
                    vt_result.append(f"► Continent: {data.get('continent', 'N/A')}")
                    vt_result.append(f"► Reputation: {data.get('reputation', 'N/A')}")
                    vt_result.append("\nLast Analysis Stats:")
                    analysis_stats = data.get("last_analysis_stats", {})
                    harmless = analysis_stats.get('harmless', 0)
                    malicious = analysis_stats.get('malicious', 0)
                    suspicious = analysis_stats.get('suspicious', 0)
                    logger.info(f"VT Analysis - Malicious: {malicious}, Suspicious: {suspicious}, Harmless: {harmless}")
                    vt_result.append(f"  • Harmless: {harmless}")
                    vt_result.append(f"  • Malicious: {malicious}")
                    vt_result.append(f"  • Suspicious: {suspicious}")
                    vt_result.append(f"  • Undetected: {analysis_stats.get('undetected', 0)}")
                    vt_result.append(f"  • Timeout: {analysis_stats.get('timeout', 0)}")
                    total_engines = sum(analysis_stats.values())
                    if total_engines > 0:
                        detection_rate = ((malicious + suspicious) / total_engines) * 100
                        vt_result.append(f"\nThreat Assessment:")
                        if detection_rate >= 15:
                            logger.warning(f"HIGH RISK IP detected: {ip_address} - Detection Rate: {detection_rate:.1f}%")
                            vt_result.append(f"  ⚠ HIGH RISK - Detection Rate: {detection_rate:.1f}%")
                        elif detection_rate >= 5:
                            logger.warning(f"MEDIUM RISK IP detected: {ip_address} - Detection Rate: {detection_rate:.1f}%")
                            vt_result.append(f"  ⚠ MEDIUM RISK - Detection Rate: {detection_rate:.1f}%")
                        else:
                            logger.info(f"LOW RISK IP: {ip_address} - Detection Rate: {detection_rate:.1f}%")
                            vt_result.append(f"  ✓ LOW RISK - Detection Rate: {detection_rate:.1f}%")
                    signals.progress.emit(80)
                    vt_result.append("\nAssociated Domains:")
                    resolutions = data.get("last_dns_records", [])
                    if resolutions:
                        logger.info(f"Found {len(resolutions)} associated domains for {ip_address}")
                        for i, record in enumerate(resolutions, 1):
                            if record.get("type") == "A" and record.get("value"):
                                vt_result.append(f"  • {record.get('value')}")
                            if i >= 10:  
                                remaining = len(resolutions) - 10
                                if remaining > 0:
                                    vt_result.append(f"  • ... and {remaining} more domains")
                                break
                    else:
                        vt_result.append("  • No associated domains found.")
                    signals.progress.emit(85)
                    try:
                        comments_url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip_address}/comments?limit=10"
                        comments_headers = {
                            "accept": "application/json",
                            "x-apikey": vt_api_key
                        }
                        comments_response = requests.get(comments_url, headers=comments_headers, timeout=10)
                        comments_data = comments_response.json()
                        comments = comments_data.get("data", [])
                        vt_comments_result = ["\n=== VirusTotal Comments for the IP Address ===\n"]
                        if not comments:
                            logger.info(f"No VirusTotal comments found for {ip_address}")
                            vt_comments_result.append("No comments found.")
                        else:
                            for idx, comment in enumerate(comments, 1):
                                attr = comment.get("attributes", {})
                                text = attr.get("text", "")
                                tags = attr.get("tags", [])
                                votes = attr.get("votes", {})
                                date = attr.get("date", None)
                                if date:
                                    date = datetime.utcfromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
                                vt_comments_result.append(f"▼ Comment {idx}:")
                                vt_comments_result.append(f"  • Text: {text}")
                                if tags:
                                    vt_comments_result.append(f"  • Tags: {', '.join(tags)}")
                                if votes:
                                    vt_comments_result.append(f"  • Votes: +{votes.get('positive', 0)}/-{votes.get('negative', 0)}")
                                vt_comments_result.append(f"  • Date: {date}")
                                if idx < len(comments):
                                    vt_comments_result.append("  " + "—" * 30)
                        vt_result.extend(vt_comments_result)
                    except Exception as e:
                        logger.error(f"Error fetching VirusTotal comments: {e}")
                        vt_result.append(f"Error fetching VirusTotal comments: {e}")
                else:
                    logger.error(f"VirusTotal API request failed with status code {response.status_code}")
                    vt_result = [f"\n=== VirusTotal Data ===\n", f"Error: VirusTotal API request failed with status code {response.status_code}"]
            except requests.RequestException as e:
                logger.error(f"VirusTotal connection error: {e}")
                vt_result = [f"\n=== VirusTotal Data ===\n", f"Error: Connection error: {e}"]
            except Exception as e:
                logger.error(f"VirusTotal unexpected error: {e}")
                vt_result = [f"\n=== VirusTotal Data ===\n", f"Error: {e}"]
        else:
            logger.warning("VirusTotal API key not available")
            vt_result = ["\n=== VirusTotal Data ===\n", "Error: VirusTotal API key not available"]
        footer = [
            "\n" + "─" * 60,
            "DISCLAIMER: This information is provided for security research purposes only.",
            "Always verify data through multiple sources before taking action.",
            "─" * 60
        ]
        signals.progress.emit(95)
        combined_result = "\n".join(report_header + tor_result + shodan_result + ip_api_result + vt_result + footer)
        signals.progress.emit(100)
        signals.finished.emit(combined_result)
    except Exception as e:
        logger.error(f"Unexpected error during IP lookup for {ip_address}: {e}")
        signals.error.emit(f"Unexpected error: {e}")

def fetch_ip_location(ip_address, db_path, get_shodan_api_key, get_vt_api_key, result_text, submit_button):
    submit_button.setEnabled(False)
    submit_button.setText("Searching...")
    result_text.clear()
    result_text.setPlainText("Starting search...")
    signals = WorkerSignals()
    
    def on_progress(value):
        result_text.setPlainText(f"Searching... {value}% complete")
    
    def on_finished(result):
        result_text.setPlainText(result)
        highlight_headers(result_text)
        submit_button.setEnabled(True)
        submit_button.setText("Submit")
    
    def on_error(error_msg):
        result_text.setPlainText(f"Error during lookup: {error_msg}")
        submit_button.setEnabled(True)
        submit_button.setText("Submit")
        
    signals.progress.connect(on_progress)
    signals.finished.connect(on_finished)
    signals.error.connect(on_error)
    thread = threading.Thread(
        target=fetch_ip_location_threaded,
        args=(ip_address, db_path, get_shodan_api_key, get_vt_api_key, signals)
    )
    thread.daemon = True
    thread.start()

def highlight_headers(text_edit):
    try:
        header_patterns = [
            "=== VirusTotal Data ===",
            "=== Shodan Data ===",
            "=== IP-API Data ===", 
            "=== Detailes found on TOR DB ===",
            "=== VirusTotal Comments for the IP Address ==="
        ]
        format_orange = QTextCharFormat()
        format_orange.setBackground(QColor("#FFA500"))  
        format_orange.setForeground(QColor("white"))
        font = QFont("Arial", 10)
        font.setBold(True)
        format_orange.setFont(font)
        format_red = QTextCharFormat()
        format_red.setBackground(QColor("#FF0000"))  
        format_red.setForeground(QColor("white"))
        format_red.setFont(font)  
        doc_text = text_edit.toPlainText()
        for base_header in header_patterns:
            index = 0
            while True:
                index = doc_text.find(base_header, index)
                if index == -1:
                    break
                cursor = text_edit.textCursor()
                cursor.setPosition(index)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(base_header))
                cursor.mergeCharFormat(format_orange)
                index += len(base_header)
        red_highlights = ["Vulnerabilities:", "Open Ports and Services:", "  Malicious:"]
        for keyword in red_highlights:
            index = 0
            while True:
                index = doc_text.find(keyword, index)
                if index == -1:
                    break
                cursor = text_edit.textCursor()
                cursor.setPosition(index)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(keyword))
                cursor.mergeCharFormat(format_red)
                index += len(keyword)
    except Exception as e:
        logger.error(f"Error in highlighting text: {e}")

def get_api_key(db_path, key_field, ip_window=None):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {key_field} FROM user_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error while retrieving {key_field}: {e}")
        return None

def open_ip_lookup_window(parent, db_path):
    global IP_LOOKUP_WINDOW
    if IP_LOOKUP_WINDOW is not None:
        IP_LOOKUP_WINDOW.activateWindow()
        IP_LOOKUP_WINDOW.raise_()
        return
    ip_window = QWidget(parent)
    ip_window.setWindowTitle("IP Lookup")
    ip_window.resize(720, 600)
    ip_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
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
    input_label = QLabel("Enter IP Address:")
    input_label.setFont(QFont("Arial", 12))
    main_layout.addWidget(input_label)
    ip_entry = QLineEdit()
    ip_entry.setFont(QFont("Arial", 10))
    ip_entry.setPlaceholderText("e.g., 8.8.8.8")
    ip_entry.setMinimumWidth(300)
    main_layout.addWidget(ip_entry)
    buttons_layout = QHBoxLayout()
    button_names = ["VT", "OTX", "DSheild", "Talos", "Spamhaus", "Criminal-IP", "Shoden", "AbuseIPDB", "Pulsedive"]
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
        "VT": "https://www.virustotal.com/gui/ip-address/{ip}",
        "OTX": "https://otx.alienvault.com/indicator/ip/{ip}",
        "DSheild": "https://www.dshield.org/ipinfo/{ip}",
        "Talos": "https://talosintelligence.com/reputation_center/lookup?search={ip}",
        "Spamhaus": "https://check.spamhaus.org/results/?query={ip}",
        "Criminal-IP": "https://www.criminalip.io/asset/report/{ip}",
        "Shoden": "https://www.shodan.io/host/{ip}",
        "AbuseIPDB": "https://www.abuseipdb.com/check/{ip}",
        "Pulsedive": "https://pulsedive.com/indicator/{ip}"
    }
    
    def create_button_click_handler(url_template):
        def button_click_handler():
            ip = ip_entry.text().strip()
            if not ip:
                QMessageBox.warning(ip_window, "Warning", "Please enter an IP address first.")
                return
            url = url_template.format(ip=ip)
            webbrowser.open(url)
        return button_click_handler
    for name in button_names:
        button = QPushButton(name)
        button.setStyleSheet(button_style)
        button.clicked.connect(create_button_click_handler(url_templates[name]))
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
    submit_button = QPushButton("Submit")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet("background-color: #4CAF50; color: white;")
    button_layout.addStretch()
    button_layout.addWidget(submit_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)
    
    def get_shodan_api_key():
        key = get_api_key(db_path, "SHODEN_API_KEY")
        if key is None:
            pass
        return key
    
    def get_vt_api_key():
        key = get_api_key(db_path, "VT_API_KEY")
        if key is None:
            pass
        return key
    
    def on_submit():
        ip_address = ip_entry.text().strip()
        if not ip_address:
            QMessageBox.warning(ip_window, "Warning", "Please enter an IP address.")
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
                f"The following API keys are not configured: {', '.join(missing_keys)}.\n\n"
                "Some information will not be available in the results."
            )
        fetch_ip_location(
            ip_address, 
            db_path, 
            get_shodan_api_key, 
            get_vt_api_key, 
            result_text,
            submit_button
        )
    submit_button.clicked.connect(on_submit)
    ip_entry.returnPressed.connect(on_submit)
    ip_window.show()