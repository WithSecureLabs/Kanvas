# MITRE ATT&CK Mapping for Kanvas: display tactics and techniques extracted from the
# Timeline sheet of the loaded Excel workbook, with a summary count and tactic-colored list.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from helper import config, styles

logger = logging.getLogger(__name__)

ICON_SIZE = 80
TACTIC_COLORS = {
    "Initial Access": "#e57373",
    "Execution": "#FFB74D",
    "Persistence": "#FFF176",
    "Privilege Escalation": "#AED581",
    "Defense Evasion": "#4FC3F7",
    "Credential Access": "#FF8A65",
    "Discovery": "#9575CD",
    "Lateral Movement": "#4DB6AC",
    "Collection": "#F06292",
    "Command and Control": "#7986CB",
    "Exfiltration": "#A1887F",
    "Impact": "#90A4AE",
}
DEFAULT_TACTIC_COLOR = "#78909C"


def extract_tactics_techniques(workbook, sheet_name):
    sheet = workbook[sheet_name]
    headers = [cell.value for cell in sheet[1]]
    if config.COL_MITRE_TACTIC not in headers:
        return None, None, f"'{config.COL_MITRE_TACTIC}' column not found"
    mitre_tactic_index = headers.index(config.COL_MITRE_TACTIC)
    mitre_techniques_index = None
    if config.COL_MITRE_TECHNIQUE in headers:
        mitre_techniques_index = headers.index(config.COL_MITRE_TECHNIQUE)
    tactics_techniques = {}
    for row_idx in range(2, sheet.max_row + 1):
        tactic_value = sheet.cell(
            row=row_idx, column=mitre_tactic_index + 1
        ).value
        if not tactic_value or not str(tactic_value).strip():
            continue
        tactic = str(tactic_value).strip()
        technique = None
        if mitre_techniques_index is not None:
            tech_val = sheet.cell(
                row=row_idx, column=mitre_techniques_index + 1
            ).value
            technique = str(tech_val).strip() if tech_val else None
        if tactic not in tactics_techniques:
            tactics_techniques[tactic] = []
        if technique and technique not in tactics_techniques[tactic]:
            tactics_techniques[tactic].append(technique)
    technique_count = sum(
        len(techs) for techs in tactics_techniques.values()
    )
    return tactics_techniques, technique_count, None


def mitre_mapping(window):
    if not hasattr(window, "current_workbook") or not hasattr(
        window, "current_file_path"
    ):
        QMessageBox.warning(
            window,
            "Error",
            "No Excel file loaded. Please load a file first.",
        )
        return None

    mitre_window = QWidget(window)
    mitre_window.setWindowTitle("MITRE ATT&CK Mapping")
    mitre_window.setStyleSheet(styles.WINDOW_BG_WHITE)

    if sys.platform == "darwin":
        mitre_window.setWindowFlags(
            Qt.Window
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
        )
        mitre_window.setFixedSize(800, 700)
    else:
        mitre_window.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        mitre_window.setFixedSize(
            int(window.width() * 0.4), int(window.height() * 0.8)
        )

    main_layout = QVBoxLayout(mitre_window)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(15)

    header_label = QLabel("MITRE ATT&CK Tactics & Techniques Mapping")
    header_label.setFont(QFont("Arial", 18, QFont.Bold))
    header_label.setStyleSheet(styles.LABEL_HEADER_BLUE)
    header_label.setAlignment(Qt.AlignCenter)
    main_layout.addWidget(header_label)

    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setStyleSheet(styles.LINE_DIVIDER)
    line.setFixedHeight(2)
    main_layout.addWidget(line)

    stats_frame = QWidget()
    stats_layout = QHBoxLayout(stats_frame)
    stats_layout.setContentsMargins(25, 15, 25, 15)

    try:
        workbook = window.current_workbook
        sheet_name = config.SHEET_TIMELINE
        if sheet_name not in workbook.sheetnames:
            logger.error("Sheet '%s' not found in workbook", sheet_name)
            QMessageBox.critical(
                mitre_window,
                "Error",
                f"Sheet '{sheet_name}' not found in the workbook.",
            )
            return None
        tactics_techniques, technique_count, error = extract_tactics_techniques(
            workbook, sheet_name
        )
        if error:
            logger.error("%s", error)
            QMessageBox.critical(mitre_window, "Error", f"{error}.")
            return None
    except Exception as e:
        logger.error("Failed to process MITRE data: %s", e, exc_info=True)
        tactics_techniques = {}
        technique_count = 0
        QMessageBox.critical(
            mitre_window,
            "Error",
            f"Failed to calculate tactic count:\n{e}",
        )

    count_label = QLabel(str(technique_count))
    count_label.setFont(QFont("Arial", 28, QFont.Bold))
    count_label.setStyleSheet(styles.LABEL_COUNT_RED)
    desc_label = QLabel("Detections Mapped")
    desc_label.setFont(QFont("Arial", 16))
    desc_label.setStyleSheet(styles.LABEL_DESC_DARK)

    icon_label = QLabel()
    try:
        pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#cc3333"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, ICON_SIZE, ICON_SIZE)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 28, QFont.Bold))
        painter.drawText(
            pixmap.rect(), Qt.AlignCenter, str(technique_count)
        )
        painter.end()
        icon_label.setPixmap(pixmap)
    except Exception as e:
        logger.error("Error creating pixmap: %s", e)
        icon_label = count_label

    stats_layout.addWidget(icon_label)
    stats_layout.addSpacing(15)
    stats_layout.addWidget(desc_label)
    stats_layout.addStretch()
    main_layout.addWidget(stats_frame)

    info_label = QLabel(
        "The following MITRE ATT&CK tactics and techniques were identified:"
    )
    info_label.setStyleSheet(styles.LABEL_INFO_ITALIC)
    main_layout.addWidget(info_label)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet(styles.SCROLL_AREA_NO_BORDER)
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setContentsMargins(10, 10, 10, 10)
    content_layout.setSpacing(10)

    for tactic, techniques in tactics_techniques.items():
        tactic_widget = QWidget()
        tactic_layout = QVBoxLayout(tactic_widget)
        tactic_layout.setContentsMargins(0, 0, 0, 0)
        tactic_layout.setSpacing(0)
        tactic_header = QLabel(str(tactic))
        tactic_header.setFont(QFont("Arial", 10, QFont.Bold))
        tactic_color = TACTIC_COLORS.get(tactic, DEFAULT_TACTIC_COLOR)
        tactic_header.setStyleSheet(
            styles.get_tactic_header_style(tactic_color)
        )
        tactic_header.setFixedHeight(22)
        tactic_layout.addWidget(tactic_header)
        tech_container = QWidget()
        tech_container.setStyleSheet(styles.CONTAINER_TRANSPARENT)
        tech_layout = QVBoxLayout(tech_container)
        tech_layout.setSpacing(2)
        tech_layout.setContentsMargins(10, 5, 10, 5)
        for tech in techniques:
            tech_row = QHBoxLayout()
            tech_row.setSpacing(2)
            bullet = QLabel("•")
            bullet.setFont(QFont("Arial", 10))
            bullet.setFixedWidth(12)
            tech_label = QLabel(str(tech))
            tech_label.setFont(QFont("Arial", 9))
            tech_label.setWordWrap(True)
            tech_row.addWidget(bullet)
            tech_row.addWidget(tech_label, 1)
            tech_layout.addLayout(tech_row)
        if not techniques:
            no_tech = QLabel("No specific techniques identified")
            no_tech.setStyleSheet(styles.LABEL_MUTED_ITALIC)
            tech_layout.addWidget(no_tech)
        tactic_layout.addWidget(tech_container)
        content_layout.addWidget(tactic_widget)
        content_layout.addSpacing(2)

    if not tactics_techniques:
        empty_label = QLabel(
            "No MITRE ATT&CK tactics found in the data."
        )
        empty_label.setStyleSheet(styles.LABEL_EMPTY_MUTED)
        empty_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(empty_label)

    scroll_area.setWidget(content_widget)
    main_layout.addWidget(scroll_area)

    footer = QLabel(
        "Based on MITRE ATT&CK® Framework - https://attack.mitre.org/"
    )
    footer.setStyleSheet(styles.LABEL_FOOTER)
    footer.setAlignment(Qt.AlignRight)
    main_layout.addWidget(footer)

    if sys.platform == "darwin":
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 10, 0, 10)
        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
        close_button.clicked.connect(mitre_window.close)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        main_layout.addWidget(button_frame)

    window.mitre_window = mitre_window
    mitre_window.show()
    return mitre_window
