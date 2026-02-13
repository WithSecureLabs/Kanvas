# VERIS (Vocabulary for Event Recording & Incident Sharing) window for Kanvas:
# edit and export VERIS incident metadata from the VERIS sheet in the loaded workbook.
# Reviewed on 01/02/2026 by Jinto Antony

import csv
import logging
import sys
from datetime import datetime

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from helper import config

logger = logging.getLogger(__name__)

VERIS_GROUPINGS = [
    ("Timeline", "timeline."),
    ("Victim", "victim."),
    ("Actors", "actor."),
    ("Action", "action."),
    ("Asset", "asset."),
    ("Attribute", "attribute."),
    ("Plus", "plus."),
]
VERIS_REQUIRED_COLUMNS = ["meta", "meta-value"]
DWELL_TIME_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
COMPROMISE_META_KEY = "timeline.incident.compromise"
DISCOVERY_META_KEY = "timeline.incident.discovery"
EXFILTRATION_META_KEY = "timeline.incident.exfiltration"


def get_widget_value(widget):
    if hasattr(widget, "text"):
        return widget.text()
    if hasattr(widget, "toPlainText"):
        return widget.toPlainText()
    return ""


def get_editable_style(font_size):
    return f"""
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
            logger.error("Failed to initialize VERIS window: %s", e)
            raise

    def setup_window(self):
        self.setWindowTitle(
            "VERIS - Vocabulary for Event Recording & Incident Sharing"
        )
        if sys.platform == "darwin":
            self.setWindowFlags(
                Qt.Window
                | Qt.CustomizeWindowHint
                | Qt.WindowTitleHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowMinimizeButtonHint
            )
            self.setFixedSize(1000, 800)
        else:
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowTitleHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowMinimizeButtonHint
                | Qt.WindowMaximizeButtonHint
            )
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
        save_button.setStyleSheet(
            f"background-color: #e74c3c; color: white; "
            f"font-weight: bold; font-size: {button_font_size};"
        )
        save_button.clicked.connect(self.save_changes)
        csv_button = QPushButton("Export CSV")
        csv_button.setFixedWidth(100)
        csv_button.setStyleSheet(
            f"background-color: #3498db; color: white; "
            f"font-weight: bold; font-size: {button_font_size};"
        )
        csv_button.clicked.connect(self.export_csv)
        txt_button = QPushButton("Export TXT")
        txt_button.setFixedWidth(100)
        txt_button.setStyleSheet(
            f"background-color: #2ecc71; color: white; "
            f"font-weight: bold; font-size: {button_font_size};"
        )
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
            logger.error("Failed to load VERIS data: %s", e)
            self.handle_error(f"Failed to load VERIS data: {e}")

    def validate_workbook(self):
        if not hasattr(self.parent_window, "current_workbook"):
            logger.warning("No Excel file loaded in parent window")
            QMessageBox.warning(
                self,
                "Warning",
                "No Excel file loaded. Please load a file first "
                "using the 'Import data' button.",
            )
            return False
        workbook = self.parent_window.current_workbook
        if config.SHEET_VERIS not in workbook.sheetnames:
            logger.warning(
                "VERIS sheet not found. Available sheets: %s",
                workbook.sheetnames,
            )
            QMessageBox.warning(
                self,
                "Warning",
                f"No '{config.SHEET_VERIS}' sheet found in the "
                "loaded Excel file.",
            )
            return False
        self.sheet = workbook[config.SHEET_VERIS]
        return True

    def load_dataframe(self):
        try:
            data = []
            headers = [cell.value for cell in self.sheet[1]]
            for row in self.sheet.iter_rows(min_row=2):
                row_data = [cell.value for cell in row]
                data.append(row_data)
            self.df = pd.DataFrame(data, columns=headers)
        except Exception as e:
            logger.error("Error loading DataFrame: %s", e)
            raise

    def validate_dataframe(self):
        missing = set(VERIS_REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            logger.error(
                "Missing required columns: %s. Available: %s",
                missing,
                list(self.df.columns),
            )
            QMessageBox.warning(
                self,
                "Warning",
                "VERIS sheet must have 'meta' and 'meta-value' columns.",
            )
            return False
        return True

    def display_veris_data(self):
        masks = {
            name: self.df["meta"].astype(str).str.startswith(prefix)
            for name, prefix in VERIS_GROUPINGS
        }
        self.create_tabs(masks)
        self.populate_tabs(masks)
        self.tab_widget.setCurrentIndex(0)

    def create_tabs(self, masks):
        for section_name, prefix in VERIS_GROUPINGS:
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
        scroll_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.addWidget(scroll_area)
        self.tab_widget.addTab(tab_widget, tab_name)
        self.tab_layouts[tab_name] = form_layout

    def populate_tabs(self, masks):
        for tab_name, form_layout in self.tab_layouts.items():
            if tab_name == "Other":
                grouped_mask = pd.Series(False, index=self.df.index)
                for mask in masks.values():
                    grouped_mask |= mask
                other_rows = self.df[~grouped_mask]
                start_row = 0
                for idx, row in other_rows.iterrows():
                    start_row = self.add_form_entry_to_tab(
                        row, start_row, form_layout
                    )
            else:
                prefix_map = dict(VERIS_GROUPINGS)
                if tab_name in prefix_map:
                    section_rows = self.df[masks[tab_name]]
                    start_row = 0
                    for idx, row in section_rows.iterrows():
                        start_row = self.handle_special_entries_in_tab(
                            row, start_row, form_layout
                        )

    def handle_special_entries_in_tab(
        self, row, start_row, form_layout
    ):
        meta_key = str(row["meta"])
        if (
            meta_key.strip().lower()
            == EXFILTRATION_META_KEY
        ):
            start_row = self.add_form_entry_to_tab(
                row, start_row, form_layout
            )
            start_row = self.add_dwell_time_entry_to_tab(
                row, start_row, form_layout
            )
        else:
            start_row = self.add_form_entry_to_tab(
                row, start_row, form_layout
            )
        return start_row

    def add_form_entry_to_tab(self, row, start_row, form_layout):
        meta_key = str(row["meta"])
        meta_value = (
            ""
            if pd.isna(row["meta-value"])
            else str(row["meta-value"])
        )
        label = QLabel(f"{meta_key}:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        widget = self.create_widget_for_value(meta_key, meta_value)
        form_layout.addWidget(label, start_row, 0)
        form_layout.addWidget(widget, start_row, 1)
        self.meta_entries.append((meta_key, widget))
        return start_row + 1

    def create_widget_for_value(self, meta_key, meta_value):
        font_size = "10pt" if sys.platform == "win32" else "11pt"
        editable_style = get_editable_style(font_size)
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

    def add_dwell_time_entry_to_tab(
        self, current_row, start_row, form_layout
    ):
        compromise_idx = self.find_row_idx(COMPROMISE_META_KEY)
        compromise_val = ""
        if compromise_idx is not None:
            val = self.df.loc[compromise_idx, "meta-value"]
            compromise_val = "" if pd.isna(val) else str(val)
        else:
            logger.warning(
                "Compromise date not found for dwell time calculation"
            )

        discovery_idx = self.find_row_idx(DISCOVERY_META_KEY)
        discovery_val = ""
        if discovery_idx is not None:
            val = self.df.loc[discovery_idx, "meta-value"]
            discovery_val = "" if pd.isna(val) else str(val)
        else:
            logger.warning(
                "Discovery date not found for dwell time calculation"
            )

        dwell_days = self.calculate_dwell_time(
            compromise_val, discovery_val
        )
        dwell_label = QLabel("Dwell Time (days):")
        dwell_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        dwell_label.setStyleSheet(
            "font-weight: bold; color: white; background-color: red;"
        )
        dwell_entry = QLineEdit()
        dwell_entry.setText(dwell_days)
        dwell_entry.setReadOnly(True)
        font_size = "10pt" if sys.platform == "win32" else "11pt"
        dwell_entry.setStyleSheet(get_editable_style(font_size))
        form_layout.addWidget(dwell_label, start_row, 0)
        form_layout.addWidget(dwell_entry, start_row, 1)
        self.meta_entries.append(("Dwell Time", dwell_entry))
        return start_row + 1

    def export_csv(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export VERIS Data as CSV",
                "veris_data.csv",
                "CSV files (*.csv)",
            )
            if file_path:
                with open(
                    file_path, "w", newline="", encoding="utf-8"
                ) as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["VERIS Field", "Value"])
                    for meta_key, widget in self.meta_entries:
                        value = get_widget_value(widget)
                        writer.writerow([meta_key, value])
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"VERIS data exported to:\n{file_path}",
                )
                logger.info("VERIS data exported to CSV: %s", file_path)
        except Exception as e:
            logger.error("Failed to export CSV: %s", e)
            QMessageBox.critical(
                self, "Export Error", f"Failed to export CSV: {e}"
            )

    def export_txt(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export VERIS Data as TXT",
                "veris_data.txt",
                "Text files (*.txt)",
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as txtfile:
                    txtfile.write("VERIS Data Export\n")
                    txtfile.write("=" * 50 + "\n\n")
                    for meta_key, widget in self.meta_entries:
                        value = get_widget_value(widget)
                        txtfile.write(f"{meta_key}: {value}\n")
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"VERIS data exported to:\n{file_path}",
                )
                logger.info("VERIS data exported to TXT: %s", file_path)
        except Exception as e:
            logger.error("Failed to export TXT: %s", e)
            QMessageBox.critical(
                self, "Export Error", f"Failed to export TXT: {e}"
            )

    def save_changes(self):
        try:
            if (
                not hasattr(self.parent_window, "current_file_path")
                or not self.parent_window.current_file_path
            ):
                logger.warning("No file path available for saving")
                QMessageBox.warning(
                    self,
                    "Save Error",
                    "No file path available. Please ensure an "
                    "Excel file is loaded.",
                )
                return

            for meta_key, widget in self.meta_entries:
                if meta_key == "Dwell Time":
                    continue
                new_value = get_widget_value(widget)
                row_idx = self.find_row_idx(meta_key)
                if row_idx is not None:
                    self.df.at[row_idx, "meta-value"] = new_value
                    logger.info("Updated %s: %s", meta_key, new_value)

            for row in self.sheet.iter_rows(min_row=2):
                for cell in row:
                    cell.value = None

            for idx, row in self.df.iterrows():
                excel_row = idx + 2
                for col_idx, value in enumerate(row):
                    cell = self.sheet.cell(
                        row=excel_row, column=col_idx + 1
                    )
                    cell.value = value

            self.parent_window.current_workbook.save(
                self.parent_window.current_file_path
            )

            QMessageBox.information(
                self,
                "Save Successful",
                "VERIS data has been saved successfully!",
            )
            logger.info("VERIS data saved successfully")

        except Exception as e:
            logger.error("Failed to save VERIS data: %s", e)
            QMessageBox.critical(
                self, "Save Error", f"Failed to save changes: {e}"
            )

    def find_row_idx(self, meta_key):
        for idx, row in self.df.iterrows():
            if (
                str(row["meta"]).strip().lower()
                == meta_key.strip().lower()
            ):
                logger.debug("Found row at index %s", idx)
                return idx
        return None

    def calculate_dwell_time(self, compromise_date, discovery_date):
        try:
            if compromise_date and discovery_date:
                comp_dt = datetime.strptime(
                    compromise_date.strip(), DWELL_TIME_DATE_FORMAT
                )
                disc_dt = datetime.strptime(
                    discovery_date.strip(), DWELL_TIME_DATE_FORMAT
                )
                dwell_days = (disc_dt - comp_dt).days
                return str(dwell_days)
            logger.warning(
                "Missing compromise or discovery date for "
                "dwell time calculation"
            )
        except ValueError as e:
            logger.error(
                "Date parsing error in dwell time calculation: %s",
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error calculating dwell time: %s", e
            )
        return ""

    def handle_error(self, error_message):
        logger.error("Handling error: %s", error_message)
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
        logger.error("Failed to create VERIS window: %s", e)
        raise
