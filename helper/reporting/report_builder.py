"""
Report Builder UI for Kanvas: dialogs for report sections, header/footer options,
recommendations and investigation summary file selection, and report generation.
Cross-platform (Windows, macOS, Linux). Revised on 01/02/2026 by Jinto Antony
"""

import logging
import re
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from helper import config, styles
from helper.reporting.report_engine import ReportEngine

logger = logging.getLogger(__name__)

REPORT_SECTIONS = [
    ("Incident Timeline", config.SHEET_TIMELINE),
    ("Lateral Movement", config.SHEET_TIMELINE),
    ("MITRE ATT&CK Tactics & Techniques Mapping", config.SHEET_TIMELINE),
    ("Compromised Systems", config.SHEET_SYSTEMS),
    ("Compromised Accounts", config.SHEET_ACCOUNTS),
    ("IOC (Indicators of Compromise)", config.SHEET_INDICATORS),
    ("Evidence Tracker", config.SHEET_EVIDENCE_TRACKER),
    ("VERIS (Vocabulary for Event Recording and Incident Sharing)", "VERIS"),
]


def parse_markdown_headings(file_path: str, level: int = 2):
    path = Path(file_path) if file_path else None
    if not path or not path.is_file():
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Could not read recommendations file for headings: %s", e)
        return []
    headings = []
    pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    for m in pattern.finditer(content):
        prefix, text = m.group(1), m.group(2).strip()
        if len(prefix) == level:
            headings.append((len(prefix), text))
    return headings


def filter_markdown_by_headings(file_path: str, selected_headings: list) -> str:
    path = Path(file_path) if file_path else None
    if not path or not path.is_file():
        return ""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Could not read recommendations file for filtering: %s", e)
        return ""
    if not selected_headings:
        return ""
    selected_set = {h.strip() for h in selected_headings}
    parts = re.split(r'\n(?=^##\s+)', content, flags=re.MULTILINE)
    result = []
    for part in parts:
        part = part.rstrip()
        if not part:
            continue
        if part.startswith("## "):
            first_line = part.split("\n", 1)[0]
            heading_text = first_line[3:].strip()
            if heading_text in selected_set:
                result.append(part)
    return "\n\n".join(result) if result else ""


def extract_markdown_section_by_heading(file_path: str, heading_text: str) -> str:
    path = Path(file_path) if file_path else None
    if not path or not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.warning("Could not read file for Case Summary: %s", e)
        return ""
    heading_lower = heading_text.strip().lower()
    in_section = False
    result = []
    heading_pattern = re.compile(r"^#+\s+(.+)$")
    for line in lines:
        m = heading_pattern.match(line.strip())
        if m:
            current_heading = m.group(1).strip().lower()
            if current_heading == heading_lower:
                in_section = True
                continue
            if in_section:
                break
        elif in_section:
            result.append(line)
    return "\n".join(result).strip() if result else ""


class RecommendationsSectionDialog(QDialog):

    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.setWindowTitle("Choose recommendations to include")
        self.file_path = file_path
        self.heading_checkboxes = []
        self.selected_headings = []
        self.setMinimumSize(480, 400)
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        
        info = QLabel("Only level-2 headings (##) from the file are listed below. Select which sections to include in the report:")
        info.setWordWrap(True)
        info.setStyleSheet(styles.LABEL_INFO_ITALIC_10PT)
        layout.addWidget(info)
        
        headings = parse_markdown_headings(self.file_path, level=2)
        if not headings:
            layout.addWidget(QLabel("No level-2 headings (##) found in this file. The full file will be used."))
            self.no_headings_found = True
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(self.accept)
            btn_layout.addWidget(ok_btn)
            layout.addLayout(btn_layout)
            return
        self.no_headings_found = False
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignTop)
        
        for _level, text in headings:
            label = "## %s" % text
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.heading_checkboxes.append((text, cb))
            scroll_layout.addWidget(cb)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select all")
        select_all_btn.clicked.connect(self.select_all)
        select_none_btn = QPushButton("Select none")
        select_none_btn.clicked.connect(self.select_none)
        btn_row.addWidget(select_all_btn)
        btn_row.addWidget(select_none_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.on_ok)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(ok_btn)
        dialog_buttons.addWidget(cancel_btn)
        layout.addLayout(dialog_buttons)
    
    def select_all(self):
        for _text, cb in self.heading_checkboxes:
            cb.setChecked(True)

    def select_none(self):
        for _text, cb in self.heading_checkboxes:
            cb.setChecked(False)

    def on_ok(self):
        self.selected_headings = [text for text, cb in self.heading_checkboxes if cb.isChecked()]
        self.accept()

    def get_selected_headings(self):
        return self.selected_headings if not self.no_headings_found else None


class ReportSectionsDialog(QDialog):

    def __init__(self, parent=None, initial_selections=None, sheet_names=None):
        super().__init__(parent)
        self.setWindowTitle("Select Report Sections")
        self.setMinimumSize(420, 380)
        self.initial_selections = initial_selections or {}
        self.sheet_names = set(sheet_names) if sheet_names else None
        self.section_checkboxes = {}
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        info = QLabel("Check the sections to include in the report (sheets must exist in the workbook):")
        info.setStyleSheet(styles.LABEL_INFO_ITALIC_10PT)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignTop)
        
        for label, sheet_name in REPORT_SECTIONS:
            display_label = "%s (xlsx sheet = %s)" % (label, sheet_name)
            cb = QCheckBox(display_label)
            checked = self.initial_selections.get(label, True)
            cb.setChecked(checked)
            cb.setToolTip("Includes workbook sheet: %s" % sheet_name)
            if self.sheet_names is not None:
                cb.setEnabled(sheet_name in self.sheet_names)
            self.section_checkboxes[label] = cb
            scroll_layout.addWidget(cb)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        select_all_btn = QPushButton("Select All")
        select_none_btn = QPushButton("Select None")
        select_all_btn.clicked.connect(self.select_all_sections)
        select_none_btn.clicked.connect(self.select_no_sections)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(select_none_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
    
    def get_selections(self):
        return {label: cb.isChecked() for label, cb in self.section_checkboxes.items()}

    def select_all_sections(self):
        for cb in self.section_checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(True)

    def select_no_sections(self):
        for cb in self.section_checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(False)


HEADER_OPTION_KEYS = ["include_headers", "author", "generated", "source", "reviewed_by", "case_id"]
HEADER_OPTION_LABELS = {
    "include_headers": "Include Header",
    "author": "Author",
    "generated": "Generated on",
    "source": "Source SOD File",
    "reviewed_by": "Reviewed by",
    "case_id": "Case ID",
}

CONFIDENTIALITY_NONE = "(None)"
CONFIDENTIALITY_CHOICES = [CONFIDENTIALITY_NONE, "Public", "Internal", "Confidential", "Restricted", "Secret"]
FOOTER_OPTION_KEYS = ["include_footers", "report_generated_on", "contact", "contact_number", "website", "reviewed_by", "case_id"]
FOOTER_OPTION_LABELS = {
    "include_footers": "Include Footer",
    "report_generated_on": "Report generated on",
    "contact": "Contact Email",
    "contact_number": "Contact Number",
    "website": "Website",
    "reviewed_by": "Reviewed by",
    "case_id": "Case ID",
}


class HeaderOptionsDialog(QDialog):

    def __init__(self, parent=None, initial_options=None):
        super().__init__(parent)
        self.setWindowTitle("Header options")
        self.setMinimumSize(360, 260)
        self.initial_options = initial_options or {}
        self.checkboxes = {}
        self.build_ui()

    def update_header_sub_options_state(self):
        include_headers = self.checkboxes["include_headers"].isChecked()
        for key in HEADER_OPTION_KEYS:
            if key == "include_headers":
                continue
            cb = self.checkboxes[key]
            cb.setEnabled(include_headers)
            if not include_headers:
                cb.setChecked(False)
        self.confidentiality_combo.setEnabled(include_headers)
        if not include_headers:
            self.confidentiality_combo.setCurrentIndex(0)
        if hasattr(self, "reviewed_by_input"):
            self.reviewed_by_input.setEnabled(include_headers and self.checkboxes["reviewed_by"].isChecked())
        if hasattr(self, "case_id_input"):
            self.case_id_input.setEnabled(include_headers and self.checkboxes["case_id"].isChecked())

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        for key in HEADER_OPTION_KEYS:
            cb = QCheckBox(HEADER_OPTION_LABELS.get(key, key))
            cb.setChecked(self.initial_options.get(key, True))
            self.checkboxes[key] = cb
            layout.addWidget(cb)
            if key == "reviewed_by":
                rev_layout = QHBoxLayout()
                rev_layout.addWidget(QLabel("Reviewed by:"))
                self.reviewed_by_input = QLineEdit()
                self.reviewed_by_input.setPlaceholderText("e.g. name or email")
                self.reviewed_by_input.setText(self.initial_options.get("reviewed_by_text", ""))
                rev_layout.addWidget(self.reviewed_by_input, 1)
                layout.addLayout(rev_layout)
                cb.toggled.connect(lambda _: self.update_header_sub_options_state())
            elif key == "case_id":
                case_layout = QHBoxLayout()
                case_layout.addWidget(QLabel("Case ID:"))
                self.case_id_input = QLineEdit()
                self.case_id_input.setPlaceholderText("e.g. case number")
                self.case_id_input.setText(self.initial_options.get("case_id_text", ""))
                case_layout.addWidget(self.case_id_input, 1)
                layout.addLayout(case_layout)
                cb.toggled.connect(lambda _: self.update_header_sub_options_state())
        self.checkboxes["include_headers"].toggled.connect(self.update_header_sub_options_state)
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Report confidentiality:"))
        self.confidentiality_combo = QComboBox()
        self.confidentiality_combo.addItems(CONFIDENTIALITY_CHOICES)
        saved = self.initial_options.get("confidentiality", "") or ""
        if saved and saved in CONFIDENTIALITY_CHOICES:
            idx = self.confidentiality_combo.findText(saved)
            if idx >= 0:
                self.confidentiality_combo.setCurrentIndex(idx)
        else:
            self.confidentiality_combo.setCurrentIndex(0)
        conf_layout.addWidget(self.confidentiality_combo, 1)
        layout.addLayout(conf_layout)
        self.update_header_sub_options_state()
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_options(self):
        out = {key: self.checkboxes[key].isChecked() for key in HEADER_OPTION_KEYS}
        conf = self.confidentiality_combo.currentText()
        out["confidentiality"] = "" if conf == CONFIDENTIALITY_NONE else conf
        out["reviewed_by_text"] = self.reviewed_by_input.text().strip() if hasattr(self, "reviewed_by_input") else ""
        out["case_id_text"] = self.case_id_input.text().strip() if hasattr(self, "case_id_input") else ""
        return out


class FooterOptionsDialog(QDialog):

    def __init__(self, parent=None, initial_options=None):
        super().__init__(parent)
        self.setWindowTitle("Footer options")
        self.setMinimumSize(440, 340)
        self.initial_options = initial_options or {}
        self.checkboxes = {}
        self.build_ui()

    def update_text_states(self):
        if not self.checkboxes["include_footers"].isChecked():
            self.contact_input.setEnabled(False)
            if hasattr(self, "reviewed_by_input"):
                self.reviewed_by_input.setEnabled(False)
            if hasattr(self, "case_id_input"):
                self.case_id_input.setEnabled(False)
            if hasattr(self, "contact_number_input"):
                self.contact_number_input.setEnabled(False)
            if hasattr(self, "website_input"):
                self.website_input.setEnabled(False)
        else:
            self.contact_input.setEnabled(self.checkboxes["contact"].isChecked())
            if hasattr(self, "reviewed_by_input"):
                self.reviewed_by_input.setEnabled(self.checkboxes["reviewed_by"].isChecked())
            if hasattr(self, "case_id_input"):
                self.case_id_input.setEnabled(self.checkboxes["case_id"].isChecked())
            if hasattr(self, "contact_number_input"):
                self.contact_number_input.setEnabled(self.checkboxes["contact_number"].isChecked())
            if hasattr(self, "website_input"):
                self.website_input.setEnabled(self.checkboxes["website"].isChecked())

    def update_footer_sub_options_state(self):
        include_footers = self.checkboxes["include_footers"].isChecked()
        for key in FOOTER_OPTION_KEYS:
            if key == "include_footers":
                continue
            cb = self.checkboxes[key]
            cb.setEnabled(include_footers)
            if not include_footers:
                cb.setChecked(False)
        self.update_text_states()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        for key in FOOTER_OPTION_KEYS:
            cb = QCheckBox(FOOTER_OPTION_LABELS.get(key, key))
            cb.setChecked(self.initial_options.get(key, True))
            self.checkboxes[key] = cb
            layout.addWidget(cb)
            if key == "contact":
                contact_layout = QHBoxLayout()
                contact_layout.addWidget(QLabel("Contact email/info:"))
                self.contact_input = QLineEdit()
                self.contact_input.setPlaceholderText("e.g. email@example.com")
                self.contact_input.setText(self.initial_options.get("contact_text", ""))
                contact_layout.addWidget(self.contact_input, 1)
                layout.addLayout(contact_layout)
                cb.toggled.connect(lambda _: self.update_text_states())
            elif key == "reviewed_by":
                rev_layout = QHBoxLayout()
                rev_layout.addWidget(QLabel("Reviewed by:"))
                self.reviewed_by_input = QLineEdit()
                self.reviewed_by_input.setPlaceholderText("e.g. name or email")
                self.reviewed_by_input.setText(self.initial_options.get("reviewed_by_text", ""))
                rev_layout.addWidget(self.reviewed_by_input, 1)
                layout.addLayout(rev_layout)
                cb.toggled.connect(lambda _: self.update_text_states())
            elif key == "contact_number":
                contact_num_layout = QHBoxLayout()
                contact_num_layout.addWidget(QLabel("Contact Number:"))
                self.contact_number_input = QLineEdit()
                self.contact_number_input.setPlaceholderText("e.g. phone number")
                self.contact_number_input.setText(self.initial_options.get("contact_number_text", ""))
                contact_num_layout.addWidget(self.contact_number_input, 1)
                layout.addLayout(contact_num_layout)
                cb.toggled.connect(lambda _: self.update_text_states())
            elif key == "website":
                website_layout = QHBoxLayout()
                website_layout.addWidget(QLabel("Website:"))
                self.website_input = QLineEdit()
                self.website_input.setPlaceholderText("e.g. https://example.com")
                self.website_input.setText(self.initial_options.get("website_text", ""))
                website_layout.addWidget(self.website_input, 1)
                layout.addLayout(website_layout)
                cb.toggled.connect(lambda _: self.update_text_states())
            elif key == "case_id":
                case_layout = QHBoxLayout()
                case_layout.addWidget(QLabel("Case ID:"))
                self.case_id_input = QLineEdit()
                self.case_id_input.setPlaceholderText("e.g. case number")
                self.case_id_input.setText(self.initial_options.get("case_id_text", ""))
                case_layout.addWidget(self.case_id_input, 1)
                layout.addLayout(case_layout)
                cb.toggled.connect(lambda _: self.update_text_states())
        self.checkboxes["include_footers"].toggled.connect(self.update_footer_sub_options_state)
        self.update_footer_sub_options_state()
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_options(self):
        out = {key: self.checkboxes[key].isChecked() for key in FOOTER_OPTION_KEYS}
        out["contact_text"] = self.contact_input.text().strip()
        out["contact_number_text"] = self.contact_number_input.text().strip() if hasattr(self, "contact_number_input") else ""
        out["website_text"] = self.website_input.text().strip() if hasattr(self, "website_input") else ""
        out["reviewed_by_text"] = self.reviewed_by_input.text().strip() if hasattr(self, "reviewed_by_input") else ""
        out["case_id_text"] = self.case_id_input.text().strip() if hasattr(self, "case_id_input") else ""
        return out


class ReportBuilderDialog(QDialog):

    def __init__(self, parent=None, report_engine: ReportEngine = None, workbook=None, file_path=None):
        super().__init__(parent)
        self.setWindowTitle("Report Builder")
        self.setMinimumSize(900, 700)
        self.report_engine = report_engine or ReportEngine()
        self.workbook = workbook
        self.file_path = file_path
        self.recommendations_file_path = None
        self.recommendations_selected_headings = None
        self.investigation_summary_file_path = None
        self.report_template_color = "#235AAA"
        self.section_selections = {}
        self.header_options = {k: True for k in HEADER_OPTION_KEYS}
        self.header_options["confidentiality"] = ""
        self.header_options["reviewed_by_text"] = ""
        self.header_options["case_id_text"] = ""
        self.footer_options = {k: True for k in FOOTER_OPTION_KEYS}
        self.footer_options["contact_text"] = ""
        self.footer_options["contact_number_text"] = ""
        self.footer_options["website_text"] = ""
        self.footer_options["reviewed_by_text"] = ""
        self.footer_options["case_id_text"] = ""
        self.setup_ui()
        self.load_available_sheets()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        info_group = QGroupBox("Report Settings")
        info_layout = QVBoxLayout(info_group)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Report Title:"))
        self.report_title_input = QLineEdit()
        self.report_title_input.setText("KANVAS Report - %s" % datetime.now().strftime("%Y-%m-%d"))
        title_layout.addWidget(self.report_title_input, 1)
        info_layout.addLayout(title_layout)
        
        author_layout = QHBoxLayout()
        author_layout.addWidget(QLabel("Author:"))
        self.author_input = QLineEdit()
        self.author_input.setText("KANVAS User")
        author_layout.addWidget(self.author_input, 1)
        info_layout.addLayout(author_layout)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Template color:"))
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(28, 28)
        self.color_preview.setStyleSheet(f"background-color: {self.report_template_color}; border: 1px solid #ccc; border-radius: 4px;")
        self.color_preview.setToolTip(self.report_template_color)
        color_layout.addWidget(self.color_preview)
        self.color_picker_btn = QPushButton("Choose Color...")
        self.color_picker_btn.clicked.connect(self.pick_report_template_color)
        color_layout.addWidget(self.color_picker_btn)
        self.report_font = "Inter"
        self.font_btn = QPushButton("Font: Inter")
        self.font_btn.setToolTip("Select report font")
        font_menu = QMenu(self)
        for font_name in ["Inter", "Arial", "Georgia", "Segoe UI", "Times New Roman", "Verdana"]:
            action = font_menu.addAction(font_name)
            action.triggered.connect(lambda checked, fn=font_name: self.set_report_font(fn))
        self.font_btn.setMenu(font_menu)
        color_layout.addWidget(self.font_btn)
        header_btn = QPushButton("Header Options")
        header_btn.setToolTip("Configure header options (include headers, Author, Generated, Source).")
        header_btn.clicked.connect(self.open_header_dialog)
        color_layout.addWidget(header_btn)
        footer_btn = QPushButton("Footer Options")
        footer_btn.setToolTip("Configure footer options (include footers, report generated on, contact, etc.).")
        footer_btn.clicked.connect(self.open_footer_dialog)
        color_layout.addWidget(footer_btn)
        select_sections_btn = QPushButton("Select Report Sections")
        select_sections_btn.clicked.connect(self.open_report_sections_dialog)
        select_sections_btn.setToolTip("Choose which report sections to include (sheets must exist in the workbook).")
        color_layout.addWidget(select_sections_btn)
        color_layout.addStretch()
        info_layout.addLayout(color_layout)
        
        main_layout.addWidget(info_group)
        recommendations_group = QGroupBox("Recommendations (Optional)")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        recommendations_file_layout = QHBoxLayout()
        recommendations_file_layout.addWidget(QLabel("Recommendations File:"))
        self.recommendations_file_input = QLineEdit()
        self.recommendations_file_input.setPlaceholderText("Browse to select recommendations markdown file (.md)...")
        self.recommendations_file_input.setReadOnly(True)
        recommendations_browse_btn = QPushButton("Browse...")
        recommendations_browse_btn.clicked.connect(self.browse_recommendations_file)
        recommendations_choose_btn = QPushButton("Choose sections...")
        recommendations_choose_btn.clicked.connect(self.choose_recommendations_sections)
        recommendations_clear_btn = QPushButton("Clear")
        recommendations_clear_btn.clicked.connect(self.clear_recommendations_file)
        recommendations_file_layout.addWidget(self.recommendations_file_input, 1)
        recommendations_file_layout.addWidget(recommendations_browse_btn)
        recommendations_file_layout.addWidget(recommendations_choose_btn)
        recommendations_file_layout.addWidget(recommendations_clear_btn)
        recommendations_layout.addLayout(recommendations_file_layout)
        
        recommendations_info = QLabel(
            "<b>Notes:</b><ul style='margin: 4px 0 0 0; padding-left: 20px;'>"
            "<li>Select a Markdown (.md) file to add the security recommendations.</li>"
            "<li>Use the 'Choose sections...' button to select or remove specific recommendations from the Markdown file.</li>"
            "</ul>"
        )
        recommendations_info.setStyleSheet(styles.LABEL_INFO_ITALIC_10PT)
        recommendations_info.setWordWrap(True)
        recommendations_info.setTextFormat(Qt.TextFormat.RichText)
        recommendations_layout.addWidget(recommendations_info)
        
        main_layout.addWidget(recommendations_group)
        investigation_group = QGroupBox("Investigation Summary (Optional)")
        investigation_layout = QVBoxLayout(investigation_group)
        
        investigation_file_layout = QHBoxLayout()
        investigation_file_layout.addWidget(QLabel("Investigation Summary File:"))
        self.investigation_summary_file_input = QLineEdit()
        self.investigation_summary_file_input.setPlaceholderText("Browse to select investigation summary markdown file (.md)...")
        self.investigation_summary_file_input.setReadOnly(True)
        investigation_browse_btn = QPushButton("Browse...")
        investigation_browse_btn.clicked.connect(self.browse_investigation_summary_file)
        investigation_clear_btn = QPushButton("Clear")
        investigation_clear_btn.clicked.connect(self.clear_investigation_summary_file)
        investigation_file_layout.addWidget(self.investigation_summary_file_input, 1)
        investigation_file_layout.addWidget(investigation_browse_btn)
        investigation_file_layout.addWidget(investigation_clear_btn)
        investigation_layout.addLayout(investigation_file_layout)
        
        investigation_info = QLabel(
            "<b>Notes:</b><ul style='margin: 4px 0 0 0; padding-left: 20px;'>"
            "<li>Select a Markdown (.md) file to add the investigation details to the report.</li>"
            "<li>The <b>Case Summary</b> section and <b>Diamond Model</b> section of the report will be generated based on this file.</li>"
            "</ul>"
        )
        investigation_info.setStyleSheet(styles.LABEL_INFO_ITALIC_10PT)
        investigation_info.setWordWrap(True)
        investigation_info.setTextFormat(Qt.TextFormat.RichText)
        investigation_layout.addWidget(investigation_info)
        
        main_layout.addWidget(investigation_group)
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(QLabel("Output Path:"))
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("Click Browse to select...")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_output_path)
        output_path_layout.addWidget(self.output_path_input, 1)
        output_path_layout.addWidget(browse_button)
        output_layout.addLayout(output_path_layout)
        output_info = QLabel(
            "<b>Notes:</b><ul style='margin: 4px 0 0 0; padding-left: 20px;'>"
            "<li>The report output will be saved in <b>HTML</b> format. All images used in the report are embedded as Base64.</li>"
            "<li>The <b>Incident Timeline visualization</b> and <b>Lateral Movement visualization</b> is automatically generated from the SOD file.</li>"
            "<li>The report may not display correctly if the following external links are not reachable (fonts and interactive network).</li>"
            "<li>https://fonts.googleapis.com, https://fonts.gstatic.com, https://unpkg.com/vis-network/standalone/umd/vis-network.min.js </li>"
            "</ul>"
        )
        output_info.setStyleSheet(styles.LABEL_INFO_ITALIC_10PT)
        output_info.setWordWrap(True)
        output_info.setTextFormat(Qt.TextFormat.RichText)
        output_layout.addWidget(output_info)
        main_layout.addWidget(output_group)
        button_layout = QHBoxLayout()
        generate_button = QPushButton("Generate Report")
        generate_button.setStyleSheet(styles.BUTTON_GENERATE)
        generate_button.clicked.connect(self.generate_report)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(generate_button)
        button_layout.addWidget(close_button)
        main_layout.addLayout(button_layout)
    
    def load_available_sheets(self):
        if not self.workbook:
            QMessageBox.warning(self, "No Workbook", "No Excel workbook loaded. Please load a file first.")
            logger.warning("No workbook available to load sheets for report builder.")
            return
        sheet_names = set(self.workbook.sheetnames)
        for label, sheet_name in REPORT_SECTIONS:
            self.section_selections[label] = sheet_name in sheet_names
    
    def open_report_sections_dialog(self):
        if not self.workbook:
            QMessageBox.warning(self, "No Workbook", "No Excel workbook loaded. Please load a file first.")
            return
        if not self.section_selections:
            for label, sheet_name in REPORT_SECTIONS:
                self.section_selections[label] = sheet_name in set(self.workbook.sheetnames)
        dialog = ReportSectionsDialog(
            self,
            initial_selections=self.section_selections,
            sheet_names=self.workbook.sheetnames
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.section_selections = dialog.get_selections()
            logger.info("Report section selections updated.")
    
    def open_header_dialog(self):
        dialog = HeaderOptionsDialog(self, initial_options=self.header_options)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.header_options = dialog.get_options()
            logger.info("Header options updated.")
    
    def open_footer_dialog(self):
        dialog = FooterOptionsDialog(self, initial_options=self.footer_options)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.footer_options = dialog.get_options()
            logger.info("Footer options updated.")
    
    def get_selected_sheets(self):
        if not self.workbook:
            return []
        sheet_names = set(self.workbook.sheetnames)
        seen = set()
        result = []
        for label, sheet_name in REPORT_SECTIONS:
            if sheet_name in sheet_names and self.section_selections.get(label, True):
                if sheet_name not in seen:
                    seen.add(sheet_name)
                    result.append(sheet_name)
        return result
    
    def browse_recommendations_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Recommendations File",
            "",
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if file_path:
            self.recommendations_file_path = file_path
            self.recommendations_file_input.setText(file_path)
            logger.info("Selected recommendations file: %s", file_path)
            self.open_recommendations_section_dialog()
    
    def choose_recommendations_sections(self):
        path = Path(self.recommendations_file_path) if self.recommendations_file_path else None
        if not path or not path.is_file():
            QMessageBox.information(
                self,
                "No file selected",
                "Please select a recommendations file first (Browse...)."
            )
            return
        self.open_recommendations_section_dialog()
    
    def open_recommendations_section_dialog(self):
        dlg = RecommendationsSectionDialog(self, self.recommendations_file_path)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.recommendations_selected_headings = dlg.get_selected_headings()
            logger.info("Recommendations sections selected: %s headings", len(self.recommendations_selected_headings or []))
    
    def clear_recommendations_file(self):
        self.recommendations_file_path = None
        self.recommendations_selected_headings = None
        self.recommendations_file_input.clear()
        logger.info("Cleared recommendations file path.")
    
    def browse_investigation_summary_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Investigation Summary File",
            "",
            "Markdown Files (*.md);;All Files (*)"
        )
        
        if file_path:
            self.investigation_summary_file_path = file_path
            self.investigation_summary_file_input.setText(file_path)
            logger.info("Selected investigation summary file: %s", file_path)
    
    def clear_investigation_summary_file(self):
        self.investigation_summary_file_path = None
        self.investigation_summary_file_input.clear()
        logger.info("Cleared investigation summary file path.")
    
    def pick_report_template_color(self):
        initial = QColor(self.report_template_color)
        color = QColorDialog.getColor(initial, self, "Report template color", QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.report_template_color = color.name()
            self.color_preview.setStyleSheet("background-color: %s; border: 1px solid #ccc; border-radius: 4px;" % self.report_template_color)
            self.color_preview.setToolTip(self.report_template_color)
    
    def set_report_font(self, font_name: str):
        self.report_font = font_name
        self.font_btn.setText("Font: %s" % font_name)
    
    def browse_output_path(self):
        extension = "HTML Files (*.html)"
        default_name = "KANVAS_Report_%s.html" % datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", default_name, extension
        )
        
        if file_path:
            self.output_path_input.setText(file_path)
    
    def generate_report(self):
        if not self.workbook or not self.file_path:
            QMessageBox.warning(self, "Error", "No Excel file loaded. Please load a file first.")
            return
        
        report_type = "HTML"
        html_template = "detailed"
        report_title = self.report_title_input.text().strip()
        author = self.author_input.text().strip()
        summary = extract_markdown_section_by_heading(
            self.investigation_summary_file_path, "Case Summary"
        ) if self.investigation_summary_file_path else ""
        if not summary.strip():
            summary = "No summary provided."
        
        selected_sheets = self.get_selected_sheets()
        has_markdown = bool(self.investigation_summary_file_path or self.recommendations_file_path)
        if not selected_sheets and not has_markdown:
            QMessageBox.warning(
                self,
                "Selection Error",
                "No data selected. Please select at least one report section or map a Markdown (.md) file before generating the report.",
            )
            return
        
        if not report_title:
            QMessageBox.warning(self, "Input Error", "Report title cannot be empty.")
            return
        
        output_path = self.output_path_input.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Input Error", "Please select an output path.")
            return
        
        try:
            column_selections = {}
            recommendations_content = None
            if self.recommendations_file_path and self.recommendations_selected_headings is not None:
                recommendations_content = filter_markdown_by_headings(
                    self.recommendations_file_path, self.recommendations_selected_headings
                )
            
            success = self.report_engine.generate_report(
                report_type,
                self.workbook,
                self.file_path,
                output_path,
                selected_sheets,
                report_title,
                author,
                summary,
                column_selections=column_selections,
                selected_sections=self.section_selections,
                timeline_image_path=None,
                network_image_path=None,
                html_template=html_template,
                recommendations_file_path=self.recommendations_file_path,
                recommendations_content=recommendations_content,
                investigation_summary_file_path=self.investigation_summary_file_path,
                header_options=self.header_options,
                footer_options=self.footer_options,
                report_font=self.report_font,
                report_color=self.report_template_color
            )
            
            if success:
                QMessageBox.information(
                    self, "Report Generated",
                    "HTML report saved to:\n%s" % output_path
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Report Error", "Failed to generate HTML report.")
        except Exception as e:
            logger.exception("Error generating report: %s", e)
            QMessageBox.critical(self, "Error", "Report generation failed: %s" % e)


def open_report_builder(parent=None, report_engine=None, workbook=None, file_path=None):
    dialog = ReportBuilderDialog(parent, report_engine, workbook, file_path)
    return dialog

