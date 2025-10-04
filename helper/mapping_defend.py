# code reviewed 
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, 
    QFrame, QApplication, QMessageBox, QTableView, QHeaderView, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QAbstractTableModel, QUrl
from PySide6.QtGui import QFont, QColor, QDesktopServices
import pandas as pd
import sqlite3
import re
import sys
import os
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

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
        if not index.isValid() or not (0 <= index.row() < self.rowCount() and 0 <= index.column() < self.columnCount()):
            return None
        value = self._data[index.row()][index.column()]
        if role == Qt.DisplayRole:
            return str(value) if value is not None else ""
        return None
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

def search_off_tech_ids(off_tech_ids, db_path='kanvas.db'):
    if not off_tech_ids:
        logger.warning("No off_tech_ids provided for search")
        return None
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
        WHERE off_tech_id IN ({','.join(['?']*len(off_tech_ids))})
        ORDER BY off_tech_id
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn, params=off_tech_ids)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        return None

def open_defend_window(parent=None, file_path=None):
    mitre_window = QWidget(parent)
    mitre_window.setWindowTitle("MITRE D3FEND Mapping")
    import sys
    if sys.platform == "darwin":
        mitre_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | 
                                  Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        mitre_window.setFixedSize(900, 700)
    else:
        mitre_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | 
                                  Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint |
                                  Qt.WindowMaximizeButtonHint)
        if parent:
            mitre_window.setFixedSize(int(parent.width() * 0.39), int(parent.height() * 0.8))
        else:
            mitre_window.setFixedSize(800, 600)
    unique_techniques = []
    search_techniques = []
    try:
        if not file_path or not os.path.exists(file_path):
            error_msg = f"Excel file not found: {file_path}"
            logger.error(error_msg)
            QMessageBox.critical(parent or mitre_window, "Error", error_msg)
            return None
        df = pd.read_excel(file_path, sheet_name='Timeline')
        if 'MITRE Tactic' not in df.columns or 'MITRE Techniques' not in df.columns:
            error_msg = "'MITRE Tactic' or 'MITRE Techniques' column not found in Timeline sheet."
            logger.error(error_msg)
            QMessageBox.critical(parent or mitre_window, "Error", error_msg)
            return None
        df = df[['MITRE Techniques']].dropna(subset=['MITRE Techniques'])
        if df.empty:
            warning_msg = "No MITRE techniques found in the Timeline sheet."
            logger.warning(warning_msg)
            QMessageBox.warning(parent or mitre_window, "Warning", warning_msg)
        else:
            unique_techniques = sorted(set(df['MITRE Techniques'].astype(str)))
            search_techniques = sorted(set(
                df['MITRE Techniques'].astype(str).apply(
                    lambda x: re.split(r'\s*-\s*', x)[0].strip()
                )
            ))
    except Exception as e:
        error_msg = f"Failed to process Excel file: {str(e)}"
        logger.error(error_msg)
        QMessageBox.critical(parent or mitre_window, "Error", error_msg)
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
    tech_title = QLabel("Select ATT&CK Techniques for D3FEND Mapping")
    tech_title_font = QFont("Arial", 14)
    tech_title_font.setBold(True)
    tech_title.setFont(tech_title_font)
    tech_title.setStyleSheet("color: #0077b6;")
    tech_title.setAlignment(Qt.AlignCenter)
    techniques_layout.addWidget(tech_title)
    if not unique_techniques:
        no_tech_label = QLabel("No techniques found in the Timeline sheet")
        no_tech_label.setFont(QFont("Arial", 10))
        no_tech_label.setStyleSheet("color: #555; padding-left: 30px;")
        no_tech_label.setAlignment(Qt.AlignLeft)
        techniques_layout.addWidget(no_tech_label)
    else:
        dropdown_label = QLabel("Select techniques to map:")
        dropdown_label.setFont(QFont("Arial", 10))
        dropdown_label.setStyleSheet("color: #333; margin-top: 10px;")
        techniques_layout.addWidget(dropdown_label)
        
        # Create horizontal layout for dropdown and buttons
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
            selected_technique = technique_combo.currentText()
            if selected_technique == "Select a technique..." or not selected_technique:
                QMessageBox.information(mitre_window, "Information", "Please select a technique to copy.")
                return
            QApplication.clipboard().setText(selected_technique)
            logger.info(f"Copied technique to clipboard: {selected_technique}")
            QMessageBox.information(mitre_window, "Success", "Selected technique copied to clipboard.")
        
        def on_search():
            for i in reversed(range(d3fend_layout.count())): 
                widget = d3fend_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            selected_technique = technique_combo.currentText()
            if selected_technique == "Select a technique..." or not selected_technique:
                no_results = QLabel("Please select a technique from the dropdown.")
                no_results.setStyleSheet("color: #d32f2f; font-weight: bold;")
                d3fend_layout.addWidget(no_results)
                return
            try:
                # Extract technique ID from the selected technique (e.g., "T1055 - Process Injection" -> "T1055")
                technique_id = re.split(r'\s*-\s*', selected_technique)[0].strip()
                result_df = search_off_tech_ids([technique_id])
                if result_df is not None and not result_df.empty:
                    grouped = result_df.groupby("off_tech_id")
                    display_columns = [
                        "off_artifact_label",
                        "def_tactic_label",
                        "query_def_tech_label", 
                        "def_artifact_rel_label",
                        "def_artifact_label"
                    ]
                    display_headers = [
                        "Off artifact",
                        "D3FEND Tactic",
                        "D3FEND Technique",
                        "Def rel",
                        "Def artifact"
                    ]
                    for off_tech_id, group in grouped:
                        tech_header = QLabel(f"off_tech_id: {off_tech_id}")
                        tech_header_font = QFont("Arial", 10)
                        tech_header_font.setBold(True)
                        tech_header.setFont(tech_header_font)
                        d3fend_layout.addWidget(tech_header)
                        unique_rows = group[display_columns].drop_duplicates()
                        table = QTableView()
                        model = PandasModel(unique_rows.values.tolist(), display_headers)
                        table.setModel(model)
                        header = table.horizontalHeader()
                        for i in range(len(display_headers)):
                            header.setSectionResizeMode(i, QHeaderView.Interactive)
                        table.setAlternatingRowColors(True)
                        table.setSelectionBehavior(QTableView.SelectRows)
                        table.setSortingEnabled(True)
                        table.setWordWrap(True)
                        table.resizeColumnsToContents()
                        table.setMinimumHeight(400)
                        d3fend_layout.addWidget(table)
                else:
                    no_results = QLabel("No D3FEND mappings found for the given techniques.")
                    d3fend_layout.addWidget(no_results)
            except Exception as e:
                error_msg = f"Error searching D3FEND mappings: {str(e)}"
                logger.error(error_msg)
                error_label = QLabel(error_msg)
                error_label.setStyleSheet("color: red;")
                d3fend_layout.addWidget(error_label)
        
        copy_btn = QPushButton("Copy Selected Technique")
        copy_btn.setStyleSheet("""
            background-color: #00c4b4;
            color: white;
            font-weight: bold;
            border: none;
            padding: 6px 16px;
        """)
        copy_btn.clicked.connect(copy_to_clipboard)
        dropdown_btn_layout.addWidget(copy_btn)
        
        search_btn = QPushButton("Map Selected to D3FEND")
        search_btn.setStyleSheet("""
            background-color: #0077b6;
            color: white;
            font-weight: bold;
            border: none;
            padding: 6px 16px;
        """)
        search_btn.clicked.connect(on_search)
        dropdown_btn_layout.addWidget(search_btn)
        
        techniques_layout.addWidget(dropdown_btn_widget)
    
    d3fend_results = QWidget()
    d3fend_layout = QVBoxLayout(d3fend_results)
    d3fend_layout.setContentsMargins(0, 0, 0, 0)
    
    help_text = QLabel("What to do next")
    help_text.setFont(QFont("Arial", 12, QFont.Bold))
    techniques_layout.addWidget(help_text)
    additional_help = QLabel("Alternatively, you can copy the attacks and search directly on https://d3fend.mitre.org/tools/attack-extractor")
    additional_help.setWordWrap(True)
    techniques_layout.addWidget(additional_help)
    link_label = QLabel()
    link_label.setOpenExternalLinks(True)
    link_label.setText("<a href='https://d3fend.mitre.org/tools/attack-extractor'>https://d3fend.mitre.org/tools/attack-extractor</a>")
    link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    def open_url():
        logger.info("Opening external URL: https://d3fend.mitre.org/tools/attack-extractor")
        QDesktopServices.openUrl(QUrl("https://d3fend.mitre.org/tools/attack-extractor"))
    link_label.linkActivated.connect(open_url)
    techniques_layout.addWidget(link_label)
    scroll_layout.addWidget(techniques_widget)
    scroll_layout.addWidget(d3fend_results)
    scroll_layout.addStretch(1)
    scroll_area.setWidget(scroll_content)
    main_layout.addWidget(scroll_area)
    
    # Add close button only on macOS (like VERIS window)
    # Windows users can use the standard close button in title bar
    if sys.platform == "darwin":  # macOS
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 10, 0, 10)
        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.setStyleSheet("background-color: #4CAF50; color: white;")
        close_button.clicked.connect(mitre_window.close)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        main_layout.addWidget(button_frame)
    
    mitre_window.show()
    return mitre_window