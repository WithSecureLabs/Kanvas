# MITRE D3FEND Mapping for Kanvas: map ATT&CK techniques from the Timeline sheet to
# D3FEND countermeasures via the defend database; supports technique selection and lookup.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import os
import re
import sys

import pandas as pd
import sqlite3
from PySide6.QtCore import Qt, QAbstractTableModel, QUrl
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from helper import config, styles

logger = logging.getLogger(__name__)

D3FEND_ATTACK_EXTRACTOR_URL = (
    "https://d3fend.mitre.org/tools/attack-extractor"
)
DEFAULT_DB_PATH = "kanvas.db"
DISPLAY_COLUMNS = [
    "off_artifact_label",
    "def_tactic_label",
    "query_def_tech_label",
    "def_artifact_rel_label",
    "def_artifact_label",
]
DISPLAY_HEADERS = [
    "Off artifact",
    "D3FEND Tactic",
    "D3FEND Technique",
    "Def rel",
    "Def artifact",
]


class PandasModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (
            0 <= index.row() < self.rowCount()
            and 0 <= index.column() < self.columnCount()
        ):
            return None
        value = self._data[index.row()][index.column()]
        if role == Qt.DisplayRole:
            return str(value) if value is not None else ""
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None


def search_off_tech_ids(off_tech_ids, db_path=DEFAULT_DB_PATH):
    if not off_tech_ids:
        logger.warning("No off_tech_ids provided for search")
        return None
    placeholders = ",".join(["?"] * len(off_tech_ids))
    query = f"""
        SELECT
            off_tech_id,
            off_artifact_rel_label,
            off_artifact_label,
            def_tactic_label,
            query_def_tech_label,
            def_artifact_rel_label,
            def_artifact_label
        FROM defend
        WHERE off_tech_id IN ({placeholders})
        ORDER BY off_tech_id
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn, params=off_tech_ids)
        return df
    except Exception as e:
        logger.error("Database query failed: %s", e)
        return None
    finally:
        if conn:
            conn.close()


def open_defend_window(parent=None, file_path=None):
    mitre_window = QWidget(parent)
    mitre_window.setWindowTitle("MITRE D3FEND Mapping")

    if sys.platform == "darwin":
        mitre_window.setWindowFlags(
            Qt.Window
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
        )
        mitre_window.setFixedSize(900, 700)
    else:
        mitre_window.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        if parent:
            mitre_window.setFixedSize(
                int(parent.width() * 0.39), int(parent.height() * 0.8)
            )
        else:
            mitre_window.setFixedSize(800, 600)

    unique_techniques = []
    try:
        if not file_path or not os.path.exists(file_path):
            error_msg = f"Excel file not found: {file_path}"
            logger.error("%s", error_msg)
            QMessageBox.critical(
                parent or mitre_window, "Error", error_msg
            )
            return None
        df = pd.read_excel(file_path, sheet_name=config.SHEET_TIMELINE)
        if (
            config.COL_MITRE_TACTIC not in df.columns
            or config.COL_MITRE_TECHNIQUE not in df.columns
        ):
            error_msg = (
                f"'{config.COL_MITRE_TACTIC}' or "
                f"'{config.COL_MITRE_TECHNIQUE}' column not found "
                "in Timeline sheet."
            )
            logger.error("%s", error_msg)
            QMessageBox.critical(
                parent or mitre_window, "Error", error_msg
            )
            return None
        df = df[[config.COL_MITRE_TECHNIQUE]].dropna(
            subset=[config.COL_MITRE_TECHNIQUE]
        )
        if df.empty:
            warning_msg = (
                "No MITRE techniques found in the Timeline sheet."
            )
            logger.warning("%s", warning_msg)
            QMessageBox.warning(
                parent or mitre_window, "Warning", warning_msg
            )
        else:
            unique_techniques = sorted(
                set(df[config.COL_MITRE_TECHNIQUE].astype(str))
            )
    except Exception as e:
        error_msg = f"Failed to process Excel file: {e}"
        logger.error("%s", error_msg)
        QMessageBox.critical(
            parent or mitre_window, "Error", error_msg
        )

    main_layout = QVBoxLayout(mitre_window)
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_content = QWidget()
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setSpacing(10)
    techniques_widget = QWidget()
    techniques_layout = QVBoxLayout(techniques_widget)
    techniques_layout.setContentsMargins(0, 0, 0, 0)

    tech_title = QLabel(
        "Select ATT&CK Techniques for D3FEND Mapping"
    )
    tech_title_font = QFont("Arial", 14)
    tech_title_font.setBold(True)
    tech_title.setFont(tech_title_font)
    tech_title.setStyleSheet(styles.LABEL_TECH_TITLE_BLUE)
    tech_title.setAlignment(Qt.AlignCenter)
    techniques_layout.addWidget(tech_title)

    if not unique_techniques:
        no_tech_label = QLabel(
            "No techniques found in the Timeline sheet"
        )
        no_tech_label.setFont(QFont("Arial", 10))
        no_tech_label.setStyleSheet(styles.LABEL_NO_TECH)
        no_tech_label.setAlignment(Qt.AlignLeft)
        techniques_layout.addWidget(no_tech_label)
    else:
        dropdown_label = QLabel("Select techniques to map:")
        dropdown_label.setFont(QFont("Arial", 10))
        dropdown_label.setStyleSheet(styles.LABEL_DROPDOWN)
        techniques_layout.addWidget(dropdown_label)

        dropdown_btn_widget = QWidget()
        dropdown_btn_layout = QHBoxLayout(dropdown_btn_widget)
        dropdown_btn_layout.setContentsMargins(0, 5, 0, 5)
        dropdown_btn_layout.setSpacing(10)

        technique_combo = QComboBox()
        technique_combo.setFont(QFont("Arial", 10))
        technique_combo.addItem("Select a technique...")
        for tech in unique_techniques:
            technique_combo.addItem(tech)
        dropdown_btn_layout.addWidget(technique_combo)

        def copy_to_clipboard():
            selected = technique_combo.currentText()
            if (
                selected == "Select a technique..."
                or not selected
            ):
                QMessageBox.information(
                    mitre_window,
                    "Information",
                    "Please select a technique to copy.",
                )
                return
            QApplication.clipboard().setText(selected)
            logger.info("Copied technique to clipboard: %s", selected)
            QMessageBox.information(
                mitre_window,
                "Success",
                "Selected technique copied to clipboard.",
            )

        def on_search():
            for i in reversed(range(d3fend_layout.count())):
                widget = d3fend_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            selected = technique_combo.currentText()
            if (
                selected == "Select a technique..."
                or not selected
            ):
                no_results = QLabel(
                    "Please select a technique from the dropdown."
                )
                no_results.setStyleSheet(styles.LABEL_NO_RESULTS)
                d3fend_layout.addWidget(no_results)
                return
            try:
                technique_id = re.split(
                    r"\s*-\s*", selected
                )[0].strip()
                result_df = search_off_tech_ids([technique_id])
                if result_df is not None and not result_df.empty:
                    grouped = result_df.groupby("off_tech_id")
                    for off_tech_id, group in grouped:
                        tech_header = QLabel(
                            f"off_tech_id: {off_tech_id}"
                        )
                        tech_header_font = QFont("Arial", 10)
                        tech_header_font.setBold(True)
                        tech_header.setFont(tech_header_font)
                        d3fend_layout.addWidget(tech_header)
                        unique_rows = group[
                            DISPLAY_COLUMNS
                        ].drop_duplicates()
                        table = QTableView()
                        model = PandasModel(
                            unique_rows.values.tolist(),
                            DISPLAY_HEADERS,
                        )
                        table.setModel(model)
                        header = table.horizontalHeader()
                        for i in range(len(DISPLAY_HEADERS)):
                            header.setSectionResizeMode(
                                i, QHeaderView.Interactive
                            )
                        table.setAlternatingRowColors(True)
                        table.setSelectionBehavior(
                            QTableView.SelectRows
                        )
                        table.setSortingEnabled(True)
                        table.setWordWrap(True)
                        table.resizeColumnsToContents()
                        table.setMinimumHeight(400)
                        d3fend_layout.addWidget(table)
                else:
                    no_results = QLabel(
                        "No D3FEND mappings found for the "
                        "given techniques."
                    )
                    d3fend_layout.addWidget(no_results)
            except Exception as e:
                error_msg = f"Error searching D3FEND mappings: {e}"
                logger.error("%s", error_msg)
                error_label = QLabel(error_msg)
                error_label.setStyleSheet(styles.LABEL_ERROR_RED)
                d3fend_layout.addWidget(error_label)

        copy_btn = QPushButton("Copy Selected Technique")
        copy_btn.setStyleSheet(styles.BUTTON_COPY_TEAL)
        copy_btn.clicked.connect(copy_to_clipboard)
        dropdown_btn_layout.addWidget(copy_btn)

        search_btn = QPushButton("Map Selected to D3FEND")
        search_btn.setStyleSheet(styles.BUTTON_D3FEND_BLUE)
        search_btn.clicked.connect(on_search)
        dropdown_btn_layout.addWidget(search_btn)

        techniques_layout.addWidget(dropdown_btn_widget)

    d3fend_results = QWidget()
    d3fend_layout = QVBoxLayout(d3fend_results)
    d3fend_layout.setContentsMargins(0, 0, 0, 0)

    help_text = QLabel("What to do next")
    help_text.setFont(QFont("Arial", 12, QFont.Bold))
    techniques_layout.addWidget(help_text)
    additional_help = QLabel(
        f"Alternatively, you can copy the attacks and search "
        f"directly on {D3FEND_ATTACK_EXTRACTOR_URL}"
    )
    additional_help.setWordWrap(True)
    techniques_layout.addWidget(additional_help)
    link_label = QLabel()
    link_label.setOpenExternalLinks(True)
    link_label.setText(
        f"<a href='{D3FEND_ATTACK_EXTRACTOR_URL}'>"
        f"{D3FEND_ATTACK_EXTRACTOR_URL}</a>"
    )
    link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)

    def open_url():
        logger.info(
            "Opening external URL: %s",
            D3FEND_ATTACK_EXTRACTOR_URL,
        )
        QDesktopServices.openUrl(
            QUrl(D3FEND_ATTACK_EXTRACTOR_URL)
        )

    link_label.linkActivated.connect(open_url)
    techniques_layout.addWidget(link_label)
    scroll_layout.addWidget(techniques_widget)
    scroll_layout.addWidget(d3fend_results)
    scroll_layout.addStretch(1)
    scroll_area.setWidget(scroll_content)
    main_layout.addWidget(scroll_area)

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

    mitre_window.show()
    return mitre_window
