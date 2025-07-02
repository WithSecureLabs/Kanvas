from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QScrollArea, 
    QVBoxLayout, QHBoxLayout, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor
import requests
import sqlite3
import logging
import webbrowser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

def open_cve_window(parent, db_path):
    cve_window = QWidget(parent)  
    cve_window.setWindowTitle("CVE Lookup")
    cve_window.resize(720, 600)
    cve_window.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    main_layout = QVBoxLayout(cve_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    input_label = QLabel("CVE:")
    input_label.setFont(QFont("Arial", 12))
    main_layout.addWidget(input_label)
    cve_entry = QLineEdit()
    cve_entry.setFont(QFont("Arial", 10))
    cve_entry.setMinimumWidth(550)
    cve_entry.setPlaceholderText("CVE-2025-44228")
    main_layout.addWidget(cve_entry)
    buttons_layout = QVBoxLayout()
    buttons_row1 = QHBoxLayout()
    buttons_row2 = QHBoxLayout()
    buttons_row3 = QHBoxLayout()
    button_names = [
        "vulners", "cvedetails", "vulmon", "vuldb", "coalitioninc"
    ]
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
        "vulners": "https://vulners.com/cve/{cve}",
        "cvedetails": "https://www.cvedetails.com/cve/{cve}/",
        "vulmon": "https://vulmon.com/searchpage?q={cve}",
        "vuldb": "https://vuldb.com/?search",
        "coalitioninc": "https://ess.coalitioninc.com/cve/?id={cve}"

    }
    def create_button_click_handler(url_template):
        def button_click_handler():
            cve_id = cve_entry.text().strip()
            if not cve_id:
                QMessageBox.warning(cve_window, "Warning", "Please enter a CVE ID first.")
                return
                
            
            url = url_template.format(cve=cve_id)
            logger.info(f"Opening URL: {url}")
            webbrowser.open(url)
        return button_click_handler
    for i, name in enumerate(button_names):
        button = QPushButton(name)
        button.setStyleSheet(button_style)
        button.clicked.connect(create_button_click_handler(url_templates[name]))
        if i < 5:
            buttons_row1.addWidget(button)
        elif i < 9:
            buttons_row2.addWidget(button)
        else:
            buttons_row3.addWidget(button)
    buttons_layout.addLayout(buttons_row1)
    buttons_layout.addLayout(buttons_row2)
    buttons_layout.addLayout(buttons_row3)
    main_layout.addLayout(buttons_layout)
    results_label = QLabel("Results:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 15, 0, 5)
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
    button_layout.addStretch()
    button_layout.addWidget(submit_button)
    button_layout.addStretch()
    main_layout.addWidget(button_frame)
    
    def fetch_and_display_cve():
        cve_id = cve_entry.text().strip()
        result_text.clear()
        if not cve_id:
            result_text.append("Enter a CVE ID.")
            return
        try:
            url = f"https://cve.circl.lu/api/cve/{cve_id}"
            logger.info(f"Fetching data from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info("Data received from API")
        except requests.exceptions.RequestException as e:
            result_text.append(f"Error fetching data: {e}")
            logger.error(f"Request error: {e}")
            return

        cve_meta = data.get("cveMetadata", {})
        cve_id_val = cve_meta.get("cveId", cve_id)
        date_published = cve_meta.get("datePublished", "N/A")
        date_updated = cve_meta.get("dateUpdated", "N/A")
        cna = data.get("containers", {}).get("cna", {})
        affected = cna.get("affected", [{}])[0] if cna.get("affected") else {}
        vendor = affected.get("vendor", "N/A")
        product = affected.get("product", "N/A")
        descriptions = cna.get("descriptions", [])
        description = descriptions[0].get("value", "N/A") if descriptions else "N/A"
        adp_data = None
        for container in data.get("containers", {}).get("adp", []) or []:
            if container.get("title") == "CISA ADP Vulnrichment":
                adp_data = container
                break
        cwe = "N/A"
        if adp_data and adp_data.get("problemTypes"):
            problem_types = adp_data.get("problemTypes", [])[0]
            if problem_types and problem_types.get("descriptions"):
                cwe = problem_types.get("descriptions", [])[0].get("cweId", "N/A")
        cvss_score = "N/A"
        cvss_severity = "N/A"
        if adp_data and adp_data.get("metrics"):
            metrics = adp_data.get("metrics", [])[0]
            if metrics and metrics.get("cvssV3_1"):
                cvss_score = metrics.get("cvssV3_1", {}).get("baseScore", "N/A")
                cvss_severity = metrics.get("cvssV3_1", {}).get("baseSeverity", "N/A")
        kev_date_added = "N/A"
        if adp_data and adp_data.get("metrics"):
            metrics = adp_data.get("metrics", [])[0]
            if metrics and metrics.get("other") and metrics.get("other", {}).get("content"):
                kev_date_added = metrics.get("other", {}).get("content", {}).get("dateAdded", "N/A")
        known_exploited = "Yes" if kev_date_added != "N/A" else "No"
        circl_header = "=== CVE Details from cve.circl.lu ==="
        cisa_header = "=== CVE Details from CISA.GOV known Ransomware Campaign Use==="
        result_text.append(circl_header)
        result_text.append("") 
        result_text.append(f"CVE ID: {cve_id_val}")
        result_text.append(f"Published Date: {date_published}")
        result_text.append(f"Last Updated: {date_updated}")
        result_text.append(f"Vendor: {vendor}")
        result_text.append(f"Product: {product}")
        result_text.append(f"CWE: {cwe}")
        result_text.append(f"CVSS Score: {cvss_score} ({cvss_severity})")
        result_text.append(f"Known Exploited: {known_exploited}")
        if kev_date_added != "N/A":
            result_text.append(f"CISA KEV Date Added: {kev_date_added}")
        result_text.append("")
        result_text.append("--- Description ---")
        result_text.append(f"{description}")
        logger.info(f"Reading data from database: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT cveID, vendorProject, product, knownRansomwareCampaignUse FROM cisa_ran_exploit WHERE cveID = ?", (cve_id,))
            row = cursor.fetchone()
            if row:
                result_text.append("")
                result_text.append(cisa_header)
                result_text.append("")
                result_text.append(f"cveID: {row[0]}")
                result_text.append(f"vendorProject: {row[1]}")
                result_text.append(f"product: {row[2]}")
                result_text.append(f"knownRansomwareCampaignUse: {row[3]}")
            else:
                result_text.append("")
                result_text.append("No CISA ransomware exploit data found for this CVE.")
        except sqlite3.Error as e:
            error_message = f"Database error: {e}"
            logger.error(error_message)
            result_text.append(f"\n{error_message}")
        finally:
            if 'conn' in locals():
                conn.close()
        highlight_headers(result_text, [circl_header, cisa_header])
        
    def highlight_headers(text_widget, headers):
        for header in headers:
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#FFA500"))  
            fmt.setForeground(QColor("white"))  
            font = QFont("Arial", 10)
            font.setBold(True)
            fmt.setFont(font)
            cursor = text_widget.textCursor()
            cursor.movePosition(QTextCursor.Start)
            doc = text_widget.document()
            while True:
                cursor = doc.find(header, cursor)
                if cursor.isNull():
                    break
                cursor.mergeCharFormat(fmt)
    submit_button.clicked.connect(fetch_and_display_cve)
    cve_entry.returnPressed.connect(fetch_and_display_cve) 
    cve_window.show()
    parent.cve_window_ref = cve_window  
    return cve_window