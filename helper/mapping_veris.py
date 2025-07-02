from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QScrollArea, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

class VerisWindow(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.meta_entries = []
        self.df = None
        try:
            self._setup_window()
            self._setup_layout()
            self._load_and_display_data()
        except Exception as e:
            logger.error(f"Failed to initialize VERIS window: {e}")
            raise
    
    def _setup_window(self):
        self.setWindowTitle("VERIS - Vocabulary for Event Recording & Incident Sharing")
        self.setMinimumSize(800, 700)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | 
                          Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    def _setup_layout(self):
        self.main_layout = QVBoxLayout()
        title_label = QLabel("VERIS - Vocabulary for Event Recording & Incident Sharing")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label, 0, Qt.AlignCenter)
        self.scroll_area = QWidget()
        self.form_layout = QGridLayout(self.scroll_area)
        self.form_layout.setContentsMargins(20, 20, 20, 20)
        self.form_layout.setVerticalSpacing(10)
        self.form_layout.setHorizontalSpacing(15)
        scroll_widget = QScrollArea()
        scroll_widget.setWidget(self.scroll_area)
        scroll_widget.setWidgetResizable(True)
        scroll_widget.setMinimumWidth(700)
        self.main_layout.addWidget(scroll_widget)
        self.setLayout(self.main_layout)
    
    def _load_and_display_data(self):
        try:
            if not self._validate_workbook():
                logger.warning("Workbook validation failed")
                return
            self._load_dataframe()
            if not self._validate_dataframe():
                logger.warning("DataFrame validation failed")
                return
            self._display_veris_data()
        except Exception as e:
            logger.error(f"Failed to load VERIS data: {e}")
            self._handle_error(f"Failed to load VERIS data: {e}")
    
    def _validate_workbook(self):
        if not hasattr(self.parent_window, 'current_workbook'):
            logger.warning("No Excel file loaded in parent window")
            QMessageBox.warning(self, "Warning", "No Excel file loaded. Please load a file first using the 'Import data' button.")
            return False
        workbook = self.parent_window.current_workbook
        if "VERIS" not in workbook.sheetnames:
            logger.warning(f"VERIS sheet not found. Available sheets: {workbook.sheetnames}")
            QMessageBox.warning(self, "Warning", "No 'VERIS' sheet found in the loaded Excel file.")
            return False
        self.sheet = workbook["VERIS"]
        return True
    
    def _load_dataframe(self):
        try:
            data = []
            headers = [cell.value for cell in self.sheet[1]]
            row_count = 0
            for row in self.sheet.iter_rows(min_row=2):
                row_data = [cell.value for cell in row]
                data.append(row_data)
                row_count += 1
            self.df = pd.DataFrame(data, columns=headers)
        except Exception as e:
            logger.error(f"Error loading DataFrame: {e}")
            raise
    
    def _validate_dataframe(self):
        required_columns = ['meta', 'meta-value']
        missing_columns = set(required_columns) - set(self.df.columns)
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}. Available columns: {list(self.df.columns)}")
            QMessageBox.warning(self, "Warning", "VERIS sheet must have 'meta' and 'meta-value' columns.")
            return False
        return True
    
    def _display_veris_data(self):
        start_row = 0
        groupings = [
            ("Timeline", "timeline."),
            ("Victim", "victim."),
            ("Actors", "actor."),
            ("Action", "action."),
            ("Asset", "asset."),
            ("Attribute", "attribute."),
            ("Plus", "plus."),
        ]
        masks = {name: self.df['meta'].astype(str).str.startswith(prefix) 
                for name, prefix in groupings}
        start_row = self._display_ungrouped_entries(masks, start_row)
        start_row = self._display_grouped_entries(groupings, masks, start_row)
    
    def _display_ungrouped_entries(self, masks, start_row):
        grouped_mask = pd.Series(False, index=self.df.index)
        for mask in masks.values():
            grouped_mask |= mask
        other_rows = self.df[~grouped_mask]
        logger.debug(f"Found {len(other_rows)} ungrouped entries")
        for idx, row in other_rows.iterrows():
            start_row = self._add_form_entry(row, start_row)
        return start_row
    
    def _display_grouped_entries(self, groupings, masks, start_row):
        for section_name, prefix in groupings:
            section_rows = self.df[masks[section_name]]
            if len(section_rows) > 0:
                start_row = self._add_section_header(section_name, start_row)
                for idx, row in section_rows.iterrows():
                    start_row = self._handle_special_entries(row, start_row)
            else:
                logger.debug(f"Section '{section_name}' has no entries")
        return start_row
    
    def _add_section_header(self, section_name, start_row):
        section_label = QLabel(section_name)
        section_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2B2B2B;")
        section_label.setAlignment(Qt.AlignCenter)
        self.form_layout.addWidget(section_label, start_row, 0, 1, 2)
        return start_row + 1
    
    def _handle_special_entries(self, row, start_row):
        meta_key = str(row['meta'])
        if meta_key.strip().lower() == "timeline.incident.compromise":
            start_row = self._add_form_entry(row, start_row)
            start_row = self._add_dwell_time_entry(row, start_row)
        else:
            start_row = self._add_form_entry(row, start_row)
        return start_row
    
    def _add_form_entry(self, row, start_row):
        meta_key = str(row['meta'])
        meta_value = "" if pd.isna(row['meta-value']) else str(row['meta-value'])
        label = QLabel(f"{meta_key}:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        widget = self._create_widget_for_value(meta_key, meta_value)
        self.form_layout.addWidget(label, start_row, 0)
        self.form_layout.addWidget(widget, start_row, 1)
        self.meta_entries.append((meta_key, widget))
        return start_row + 1
    
    def _create_widget_for_value(self, meta_key, meta_value):
        if "notes" in meta_key.lower() or "summary" in meta_key.lower():
            widget = QTextEdit()
            widget.setPlainText(meta_value)
            widget.setReadOnly(True)
            widget.setMaximumHeight(100)
        else:
            widget = QLineEdit()
            widget.setText(meta_value)
            widget.setReadOnly(True)
        return widget
    
    def _add_dwell_time_entry(self, compromise_row, start_row):
        meta_value = "" if pd.isna(compromise_row['meta-value']) else str(compromise_row['meta-value'])
        discovery_idx = self._find_row_idx("timeline.incident.discovery")
        discovery_val = ""
        if discovery_idx is not None:
            discovery_val = "" if pd.isna(self.df.loc[discovery_idx, 'meta-value']) else str(self.df.loc[discovery_idx, 'meta-value'])
        else:
            logger.warning("Discovery date not found for dwell time calculation")
        dwell_days = self._calculate_dwell_time(meta_value, discovery_val)
        dwell_label = QLabel("Dwell Time (days):")
        dwell_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dwell_label.setStyleSheet("font-weight: bold; color: white; background-color: red;")
        dwell_entry = QLineEdit()
        dwell_entry.setText(dwell_days)
        dwell_entry.setReadOnly(True)
        self.form_layout.addWidget(dwell_label, start_row, 0)
        self.form_layout.addWidget(dwell_entry, start_row, 1)
        self.meta_entries.append(("Dwell Time", dwell_entry))
        return start_row + 1
    
    def _find_row_idx(self, meta_key):
        for idx, row in self.df.iterrows():
            if str(row['meta']).strip().lower() == meta_key.strip().lower():
                logger.debug(f"Found row at index {idx}")
                return idx
        return None
    
    def _calculate_dwell_time(self, compromise_date, discovery_date):
        try:
            if compromise_date and discovery_date:
                dt_format = "%Y-%m-%d %H:%M:%S"
                comp_dt = datetime.strptime(compromise_date.strip(), dt_format)
                disc_dt = datetime.strptime(discovery_date.strip(), dt_format)
                dwell_days = (disc_dt - comp_dt).days
                #logger.info(f"Dwell time calculated successfully: {dwell_days} days")
                return str(dwell_days)
            else:
                logger.warning("Missing compromise or discovery date for dwell time calculation")
        except ValueError as e:
            logger.error(f"Date parsing error in dwell time calculation: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calculating dwell time: {e}")
        return ""
    
    def _handle_error(self, error_message):
        logger.error(f"Handling error: {error_message}")
        QMessageBox.critical(self, "Error", error_message)
        error_label = QLabel(f"Error loading VERIS sheet: {error_message}")
        error_label.setStyleSheet("color: red;")
        self.form_layout.addWidget(error_label, 0, 0, 1, 2)

def open_veris_window(window):
    try:
        veris_window = VerisWindow(window)
        veris_window.show()
        return veris_window
    except Exception as e:
        logger.error(f"Failed to create VERIS window: {e}")
        raise