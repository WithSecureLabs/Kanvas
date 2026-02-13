# CVE Lookup window for Kanvas: fetch CVE details from cve.circl.lu API and CISA KEV,
# display them in a formatted view, and provide quick links to Vulners, CVE Details, etc.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import sqlite3
import webbrowser

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

logger = logging.getLogger(__name__)

CVE_CIRCL_API_BASE = "https://cve.circl.lu/api/cve"
REQUEST_TIMEOUT = 10

CVE_BUTTON_NAMES = [
    "vulners",
    "cvedetails",
    "vulmon",
    "vuldb",
    "coalitioninc",
]
CVE_URL_TEMPLATES = {
    "vulners": "https://vulners.com/cve/{cve}",
    "cvedetails": "https://www.cvedetails.com/cve/{cve}/",
    "vulmon": "https://vulmon.com/searchpage?q={cve}",
    "vuldb": "https://vuldb.com/?search",
    "coalitioninc": "https://ess.coalitioninc.com/cve/?id={cve}",
}


def highlight_headers(text_widget, headers):
    for header in headers:
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(styles.HEADER_HIGHLIGHT_BG))
        fmt.setForeground(QColor(styles.HEADER_HIGHLIGHT_FG))
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


def parse_adp_metrics(adp_data):
    cwe = "N/A"
    cvss_score = "N/A"
    cvss_severity = "N/A"
    kev_date_added = "N/A"
    if not adp_data:
        return cwe, cvss_score, cvss_severity, kev_date_added
    problem_types = (adp_data.get("problemTypes") or [{}])[0]
    if problem_types and problem_types.get("descriptions"):
        cwe = (problem_types.get("descriptions", [{}])[0].get("cweId", "N/A"))
    metrics = (adp_data.get("metrics") or [{}])[0]
    if metrics:
        cvss = metrics.get("cvssV3_1") or {}
        cvss_score = cvss.get("baseScore", "N/A")
        cvss_severity = cvss.get("baseSeverity", "N/A")
        other = metrics.get("other") or {}
        content = other.get("content") or {}
        kev_date_added = content.get("dateAdded", "N/A")
    return cwe, cvss_score, cvss_severity, kev_date_added


def open_cve_window(parent, db_path):
    cve_window = QWidget(parent.window)
    cve_window.setWindowTitle("CVE Lookup")
    cve_window.resize(720, 600)
    cve_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )
    main_layout = QVBoxLayout(cve_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)

    input_layout = QHBoxLayout()
    input_label = QLabel("CVE:")
    input_label.setFont(QFont("Arial", 12))
    input_layout.addWidget(input_label)

    cve_entry = QLineEdit()
    cve_entry.setFont(QFont("Arial", 10))
    cve_entry.setMinimumWidth(300)
    cve_entry.setPlaceholderText("CVE-2025-44228")
    input_layout.addWidget(cve_entry)

    submit_button = QPushButton("Search")
    submit_button.setFixedWidth(100)
    submit_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    input_layout.addWidget(submit_button)

    main_layout.addLayout(input_layout)

    buttons_row = QHBoxLayout()
    for name in CVE_BUTTON_NAMES:
        button = QPushButton(name)
        button.setStyleSheet(styles.BUTTON_STYLE_PINK)

        def make_handler(url_template):
            def handler():
                cve_id = cve_entry.text().strip()
                if not cve_id:
                    QMessageBox.warning(
                        cve_window, "Warning", "Please enter a CVE ID first."
                    )
                    return
                url = url_template.format(cve=cve_id)
                logger.info("Opening URL: %s", url)
                webbrowser.open(url)

            return handler

        button.clicked.connect(make_handler(CVE_URL_TEMPLATES[name]))
        buttons_row.addWidget(button)
    main_layout.addLayout(buttons_row)

    results_label = QLabel("Results:")
    results_label.setFont(QFont("Arial", 12))
    results_label.setContentsMargins(0, 15, 0, 5)
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

    def fetch_and_display_cve():
        cve_id = cve_entry.text().strip()
        result_text.clear()
        if not cve_id:
            result_text.append("Enter a CVE ID.")
            return
        try:
            url = f"{CVE_CIRCL_API_BASE}/{cve_id}"
            logger.info("Fetching data from %s", url)
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.info("Data received from API")
        except requests.exceptions.RequestException as e:
            result_text.append(f"Error fetching data: {e}")
            return
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            result_text.append(f"Unexpected error: {e}")
            return

        cve_meta = data.get("cveMetadata", {})
        cve_id_val = cve_meta.get("cveId", cve_id)
        date_published = cve_meta.get("datePublished", "N/A")
        date_updated = cve_meta.get("dateUpdated", "N/A")
        cna = data.get("containers", {}).get("cna", {})
        affected = (cna.get("affected") or [{}])[0]
        vendor = affected.get("vendor", "N/A")
        product = affected.get("product", "N/A")
        descriptions = cna.get("descriptions", [])
        description = (
            descriptions[0].get("value", "N/A") if descriptions else "N/A"
        )

        adp_data = None
        for container in (data.get("containers", {}).get("adp") or []):
            if container.get("title") == "CISA ADP Vulnrichment":
                adp_data = container
                break

        cwe, cvss_score, cvss_severity, kev_date_added = parse_adp_metrics(
            adp_data
        )
        known_exploited = "Yes" if kev_date_added != "N/A" else "No"

        circl_header = "=== CVE Details from cve.circl.lu ==="
        cisa_header = (
            "=== CVE Details from CISA.GOV known Ransomware Campaign Use==="
        )
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
        result_text.append(description)

        logger.info("Reading data from database: %s", db_path)
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cveID, vendorProject, product, knownRansomwareCampaignUse FROM cisa_ran_exploit WHERE cveID = ?",
                (cve_id,),
            )
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
                result_text.append(
                    "No CISA ransomware exploit data found for this CVE."
                )
        except sqlite3.Error as e:
            error_message = f"Database error: {e}"
            logger.error(error_message)
            result_text.append(f"\n{error_message}")
        finally:
            if conn:
                conn.close()

        highlight_headers(result_text, [circl_header, cisa_header])

    submit_button.clicked.connect(fetch_and_display_cve)
    cve_entry.returnPressed.connect(fetch_and_display_cve)
    close_button.clicked.connect(cve_window.close)
    cve_window.show()
    parent.cve_window_ref = cve_window
    return cve_window
