# code reviewed 
import sys
import logging
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QScrollArea, QGridLayout, QMessageBox, QTabWidget, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

class VerisWindow(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.meta_entries = []
        self.df = None
        try:
            self.setup_window()
            self.setup_layout()
            self.load_and_display_data()
        except Exception as e:
            logger.error(f"Failed to initialize VERIS window: {e}")
            raise
    
    def setup_window(self):
        self.setWindowTitle("VERIS - Vocabulary for Event Recording & Incident Sharing")
        if sys.platform == "darwin":  
            self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | 
                              Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
            self.setFixedSize(1000, 800)
        else:  
            self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | 
                              Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint |
                              Qt.WindowMaximizeButtonHint)
            self.setMinimumSize(800, 700)
    
    def setup_layout(self):
        self.main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumWidth(700)
        self.main_layout.addWidget(self.tab_widget)
        self.tab_layouts = {}
        
        export_frame = QWidget()
        export_layout = QHBoxLayout(export_frame)
        export_layout.setContentsMargins(0, 10, 0, 10)
        export_layout.setSpacing(10)
        button_font_size = "9pt" if sys.platform == "win32" else "10pt"
        
        save_button = QPushButton("Save Changes")
        save_button.setFixedWidth(120)
        save_button.setStyleSheet(f"background-color: #e74c3c; color: white; font-weight: bold; font-size: {button_font_size};")
        save_button.clicked.connect(self.save_changes)
        csv_button = QPushButton("Export CSV")
        csv_button.setFixedWidth(100)
        csv_button.setStyleSheet(f"background-color: #3498db; color: white; font-weight: bold; font-size: {button_font_size};")
        csv_button.clicked.connect(self.export_csv)
        txt_button = QPushButton("Export TXT")
        txt_button.setFixedWidth(100)
        txt_button.setStyleSheet(f"background-color: #2ecc71; color: white; font-weight: bold; font-size: {button_font_size};")
        txt_button.clicked.connect(self.export_txt)
        export_layout.addWidget(save_button)
        export_layout.addWidget(csv_button)
        export_layout.addWidget(txt_button)
        export_layout.addStretch()
        self.main_layout.addWidget(export_frame)
        
        self.setLayout(self.main_layout)
    
    def load_and_display_data(self):
        try:
            if not self.validate_workbook():
                logger.warning("Workbook validation failed")
                return
            self.load_dataframe()
            if not self.validate_dataframe():
                logger.warning("DataFrame validation failed")
                return
            self.display_veris_data()
        except Exception as e:
            logger.error(f"Failed to load VERIS data: {e}")
            self.handle_error(f"Failed to load VERIS data: {e}")
    
    def validate_workbook(self):
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
    
    def load_dataframe(self):
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
    
    def validate_dataframe(self):
        required_columns = ['meta', 'meta-value']
        missing_columns = set(required_columns) - set(self.df.columns)
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}. Available columns: {list(self.df.columns)}")
            QMessageBox.warning(self, "Warning", "VERIS sheet must have 'meta' and 'meta-value' columns.")
            return False
        return True
    
    def display_veris_data(self):
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
        self.create_tabs(groupings, masks)
        self.populate_tabs(groupings, masks)
        self.tab_widget.setCurrentIndex(0)
    
    def create_tabs(self, groupings, masks):
        for section_name, prefix in groupings:
            if section_name == "Plus":
                grouped_mask = pd.Series(False, index=self.df.index)
                for mask in masks.values():
                    grouped_mask |= mask
                other_rows = self.df[~grouped_mask]
                if len(other_rows) > 0:
                    self.create_tab("Other", other_rows)
            section_rows = self.df[masks[section_name]]
            if len(section_rows) > 0:
                self.create_tab(section_name, section_rows)
    
    def create_tab(self, tab_name, data_rows):
        tab_widget = QWidget()
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        form_layout = QGridLayout(scroll_widget)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setVerticalSpacing(0)
        form_layout.setHorizontalSpacing(8)
        form_layout.setRowStretch(999, 1)
        scroll_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.addWidget(scroll_area)
        self.tab_widget.addTab(tab_widget, tab_name)
        self.tab_layouts[tab_name] = form_layout
    
    def populate_tabs(self, groupings, masks):
        for tab_name, form_layout in self.tab_layouts.items():
            if tab_name == "Other":
                grouped_mask = pd.Series(False, index=self.df.index)
                for mask in masks.values():
                    grouped_mask |= mask
                other_rows = self.df[~grouped_mask]
                start_row = 0
                for idx, row in other_rows.iterrows():
                    start_row = self.add_form_entry_to_tab(row, start_row, form_layout)
            else:
                prefix_map = {name: prefix for name, prefix in groupings}
                if tab_name in prefix_map:
                    section_rows = self.df[masks[tab_name]]
                    start_row = 0
                    for idx, row in section_rows.iterrows():
                        start_row = self.handle_special_entries_in_tab(row, start_row, form_layout)
    
    def handle_special_entries_in_tab(self, row, start_row, form_layout):
        meta_key = str(row['meta'])
        if meta_key.strip().lower() == "timeline.incident.exfiltration":
            start_row = self.add_form_entry_to_tab(row, start_row, form_layout)
            start_row = self.add_dwell_time_entry_to_tab(row, start_row, form_layout)
        else:
            start_row = self.add_form_entry_to_tab(row, start_row, form_layout)
        return start_row
    
    def add_form_entry_to_tab(self, row, start_row, form_layout):
        meta_key = str(row['meta'])
        meta_value = "" if pd.isna(row['meta-value']) else str(row['meta-value'])
        label = QLabel(f"{meta_key}:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        widget = self.create_widget_for_value(meta_key, meta_value)
        form_layout.addWidget(label, start_row, 0)
        form_layout.addWidget(widget, start_row, 1)
        self.meta_entries.append((meta_key, widget))
        return start_row + 1
    
    def create_widget_for_value(self, meta_key, meta_value):
        font_size = "10pt" if sys.platform == "win32" else "11pt"
        
        editable_style = f"""
            QLineEdit {{
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 4px;
                color: #000000;
                font-family: Arial, sans-serif;
                font-size: {font_size};
                padding: 8px;
                selection-background-color: #007bff;
            }}
            QLineEdit:focus {{
                border-color: #007bff;
                background-color: #ffffff;
            }}
            QTextEdit {{
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 4px;
                color: #000000;
                font-family: Arial, sans-serif;
                font-size: {font_size};
                padding: 8px;
                selection-background-color: #007bff;
            }}
            QTextEdit:focus {{
                border-color: #007bff;
                background-color: #ffffff;
            }}
        """
        if "notes" in meta_key.lower() or "summary" in meta_key.lower():
            widget = QTextEdit()
            widget.setPlainText(meta_value)
            widget.setMaximumHeight(100)
            widget.setStyleSheet(editable_style)
        else:
            widget = QLineEdit()
            widget.setText(meta_value)
            widget.setStyleSheet(editable_style)
        return widget
    
    def add_dwell_time_entry_to_tab(self, current_row, start_row, form_layout):
        compromise_idx = self.find_row_idx("timeline.incident.compromise")
        compromise_val = ""
        if compromise_idx is not None:
            compromise_val = "" if pd.isna(self.df.loc[compromise_idx, 'meta-value']) else str(self.df.loc[compromise_idx, 'meta-value'])
        else:
            logger.warning("Compromise date not found for dwell time calculation")
        
        discovery_idx = self.find_row_idx("timeline.incident.discovery")
        discovery_val = ""
        if discovery_idx is not None:
            discovery_val = "" if pd.isna(self.df.loc[discovery_idx, 'meta-value']) else str(self.df.loc[discovery_idx, 'meta-value'])
        else:
            logger.warning("Discovery date not found for dwell time calculation")
        
        dwell_days = self.calculate_dwell_time(compromise_val, discovery_val)
        dwell_label = QLabel("Dwell Time (days):")
        dwell_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dwell_label.setStyleSheet("font-weight: bold; color: white; background-color: red;")
        dwell_entry = QLineEdit()
        dwell_entry.setText(dwell_days)
        dwell_entry.setReadOnly(True)
        
        font_size = "10pt" if sys.platform == "win32" else "11pt"
        
        dwell_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 4px;
                color: #000000;
                font-family: Arial, sans-serif;
                font-size: {font_size};
                padding: 8px;
                selection-background-color: #007bff;
            }}
            QLineEdit:focus {{
                border-color: #007bff;
                background-color: #ffffff;
            }}
        """)
        form_layout.addWidget(dwell_label, start_row, 0)
        form_layout.addWidget(dwell_entry, start_row, 1)
        self.meta_entries.append(("Dwell Time", dwell_entry))
        return start_row + 1
    
    def export_csv(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Export VERIS Data as CSV", "veris_data.csv", "CSV files (*.csv)")
            if file_path:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['VERIS Field', 'Value'])
                    for meta_key, widget in self.meta_entries:
                        if hasattr(widget, 'text'):
                            value = widget.text()
                        elif hasattr(widget, 'toPlainText'):
                            value = widget.toPlainText()
                        else:
                            value = ""
                        writer.writerow([meta_key, value])
                QMessageBox.information(self, "Export Successful", f"VERIS data exported to:\n{file_path}")
                logger.info(f"VERIS data exported to CSV: {file_path}")
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {str(e)}")
    
    def export_txt(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Export VERIS Data as TXT", "veris_data.txt", "Text files (*.txt)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as txtfile:
                    txtfile.write("VERIS Data Export\n")
                    txtfile.write("=" * 50 + "\n\n")
                    for meta_key, widget in self.meta_entries:
                        if hasattr(widget, 'text'):
                            value = widget.text()
                        elif hasattr(widget, 'toPlainText'):
                            value = widget.toPlainText()
                        else:
                            value = ""
                        txtfile.write(f"{meta_key}: {value}\n")
                QMessageBox.information(self, "Export Successful", f"VERIS data exported to:\n{file_path}")
                logger.info(f"VERIS data exported to TXT: {file_path}")
        except Exception as e:
            logger.error(f"Failed to export TXT: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export TXT: {str(e)}")
    
    def save_changes(self):
        try:
            if not hasattr(self.parent_window, 'current_file_path') or not self.parent_window.current_file_path:
                logger.warning("No file path available for saving")
                QMessageBox.warning(self, "Save Error", "No file path available. Please ensure an Excel file is loaded.")
                return
            
            for meta_key, widget in self.meta_entries:
                if meta_key == "Dwell Time":
                    continue
                    
                if hasattr(widget, 'text'):
                    new_value = widget.text()
                elif hasattr(widget, 'toPlainText'):
                    new_value = widget.toPlainText()
                else:
                    continue
                
                row_idx = self.find_row_idx(meta_key)
                if row_idx is not None:
                    self.df.at[row_idx, 'meta-value'] = new_value
                    logger.info(f"Updated {meta_key}: {new_value}")
            
            for row in self.sheet.iter_rows(min_row=2):
                for cell in row:
                    cell.value = None
            
            for idx, row in self.df.iterrows():
                excel_row = idx + 2
                for col_idx, value in enumerate(row):
                    cell = self.sheet.cell(row=excel_row, column=col_idx + 1)
                    cell.value = value
            
            self.parent_window.current_workbook.save(self.parent_window.current_file_path)
            
            QMessageBox.information(self, "Save Successful", "VERIS data has been saved successfully!")
            logger.info("VERIS data saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save VERIS data: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save changes: {str(e)}")
    
    def find_row_idx(self, meta_key):
        for idx, row in self.df.iterrows():
            if str(row['meta']).strip().lower() == meta_key.strip().lower():
                logger.debug(f"Found row at index {idx}")
                return idx
        return None
    
    def calculate_dwell_time(self, compromise_date, discovery_date):
        try:
            if compromise_date and discovery_date:
                dt_format = "%Y-%m-%d %H:%M:%S"
                comp_dt = datetime.strptime(compromise_date.strip(), dt_format)
                disc_dt = datetime.strptime(discovery_date.strip(), dt_format)
                dwell_days = (disc_dt - comp_dt).days
                return str(dwell_days)
            else:
                logger.warning("Missing compromise or discovery date for dwell time calculation")
        except ValueError as e:
            logger.error(f"Date parsing error in dwell time calculation: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calculating dwell time: {e}")
        return ""
    
    def handle_error(self, error_message):
        logger.error(f"Handling error: {error_message}")
        QMessageBox.critical(self, "Error", error_message)

VERIS_WINDOW = None

def open_veris_window(parent):
    global VERIS_WINDOW
    if VERIS_WINDOW is not None:
        VERIS_WINDOW.activateWindow()
        VERIS_WINDOW.raise_()
        return VERIS_WINDOW
    try:
        veris_window = VerisWindow(parent)
        VERIS_WINDOW = veris_window
        original_close_event = veris_window.closeEvent
        
        def custom_close_event(event):
            global VERIS_WINDOW
            VERIS_WINDOW = None
            if original_close_event:
                original_close_event(event)
        veris_window.closeEvent = custom_close_event
        
        veris_window.show()
        return veris_window
    except Exception as e:
        logger.error(f"Failed to create VERIS window: {e}")
        raise