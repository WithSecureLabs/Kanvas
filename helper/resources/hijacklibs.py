"""
HijackLibs knowledge-base window for Kanvas: loads YAML data from data/hijacklib
(recursive), provides search, vendor filter, and detail view. Cross-platform
(Windows, macOS, Linux). Revised on 01/02/2026 by Jinto Antony
"""

import logging
import re
from pathlib import Path

import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QStandardItem, QStandardItemModel, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from helper import styles

logger = logging.getLogger(__name__)

HIJACKLIBS_WINDOW = None
HIJACKLIBS_DATA_CACHE = None
DETAIL_LINE_WIDTH = 78
DETAIL_BORDER_WIDTH = 77


def load_hijacklibs_data():
    global HIJACKLIBS_DATA_CACHE
    if HIJACKLIBS_DATA_CACHE is not None:
        return HIJACKLIBS_DATA_CACHE
    hijacklibs_data = []
    base_dir = Path(__file__).parent.parent.parent
    hijacklib_dir = base_dir / "data" / "hijacklib"
    try:
        if not hijacklib_dir.exists():
            logger.error("HijackLibs directory not found: %s", hijacklib_dir)
            return []
        yml_files = [f for f in hijacklib_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".yml", ".yaml")]
        logger.info("Found %s YAML files in hijacklib directory", len(yml_files))
        if not yml_files:
            logger.warning("No YAML files found in hijacklib directory.")
            return []
        for yml_path in yml_files:
            try:
                with open(yml_path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                documents = content.split("---")
                for doc in documents:
                    doc = doc.strip()
                    if not doc or doc.startswith("#"):
                        continue
                    try:
                        hijacklib = yaml.safe_load(doc)
                        if hijacklib and ("Name" in hijacklib or "name" in hijacklib):
                            if "name" in hijacklib and "Name" not in hijacklib:
                                hijacklib["Name"] = hijacklib.pop("name")
                            try:
                                rel = yml_path.relative_to(hijacklib_dir)
                                hijacklib["file_path"] = rel.as_posix()
                            except ValueError:
                                hijacklib["file_path"] = yml_path.name
                            hijacklib["file"] = yml_path.name
                            hijacklibs_data.append(hijacklib)
                    except yaml.YAMLError as e:
                        logger.error("YAML parse error in %s: %s", yml_path, e)
                        continue
            except Exception as e:
                logger.error("Error loading %s: %s", yml_path, e)
                continue
        logger.info("Loaded %s hijacklibs from %s files", len(hijacklibs_data), len(yml_files))
    except Exception as e:
        logger.error("Error loading hijacklibs data: %s", e)
    
    HIJACKLIBS_DATA_CACHE = hijacklibs_data
    return hijacklibs_data

class YAMLHighlighter(QSyntaxHighlighter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#268bd2"))
        key_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'^(\w+):', key_format))
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#2aa198"))
        self.highlighting_rules.append((r'["\']([^"\']*)["\']', string_format))
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#859900"))
        self.highlighting_rules.append((r'^\s*-\s+', list_format))
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#93a1a1"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r'#.*$', comment_format))
    
    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = re.compile(pattern, re.MULTILINE)
            for match in expression.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

def show_detailed_view(parent, hijacklib_data):
    detail_dialog = QDialog(parent)
    hijacklib_name = hijacklib_data.get('Name', hijacklib_data.get('name', 'Unknown'))
    detail_dialog.setWindowTitle(f"HijackLib Details - {hijacklib_name}")
    detail_dialog.resize(900, 700)
    detail_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    layout = QVBoxLayout(detail_dialog)
    
    title_label = QLabel(f"HijackLib Details - {hijacklib_name}")
    title_font = QFont()
    title_font.setPointSize(14)
    title_font.setBold(True)
    title_label.setFont(title_font)
    title_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_label)
    
    text_area = QTextEdit()
    text_area.setReadOnly(True)
    text_area.setFont(QFont("Consolas", 10) or QFont("Courier New", 10))
    text_area.setStyleSheet(styles.TEXT_EDIT_KB_DETAIL_DIALOG)
    hijacklib_name = hijacklib_data.get("Name", hijacklib_data.get("name", "Unknown"))
    content = []
    content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
    name_padding = max(0, DETAIL_LINE_WIDTH - (len(hijacklib_name) + 2))
    content.append(f"║  <b>{hijacklib_name}</b>" + " " * name_padding + "║")
    content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
    content.append("")
    vuln_executables = hijacklib_data.get('VulnerableExecutables', [])
    if vuln_executables:
        exe_count = len(vuln_executables)
        hijack_type = f"DLL Sideloading ({exe_count} EXE{'s' if exe_count > 1 else ''})"
        content.append(f"┌─ <b>DLL Hijacking Type</b>")
        content.append(f"│  {hijack_type}")
        content.append("│")
        content.append("│  Copy (and optionally rename) a vulnerable application alongside a")
        content.append("│  malicious DLL to execute arbitrary code through the legitimate")
        content.append("│  application.")
        content.append("│")
        content.append("│  MITRE ATT&CK®: T1574.001 - Hijack Execution Flow: DLL")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    content.append("┌─ <b>General Information</b>")
    if hijacklib_data.get('Vendor'):
        content.append(f"│  DLL Vendor: {hijacklib_data['Vendor']}")
    if hijacklib_data.get('Author'):
        content.append(f"│  Author: {hijacklib_data['Author']}")
    if hijacklib_data.get('Created'):
        content.append(f"│  Created: {hijacklib_data['Created']}")
    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
    content.append("")
    if hijacklib_data.get('ExpectedLocations'):
        content.append("┌─ <b>Expected Locations</b>")
        for location in hijacklib_data['ExpectedLocations']:
            content.append(f"│  • {location}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if hijacklib_data.get('ExpectedSignatureInformation'):
        content.append("┌─ <b>Expected Signature Information</b>")
        for i, sig_info in enumerate(hijacklib_data['ExpectedSignatureInformation'], 1):
            if isinstance(sig_info, dict):
                for key, value in sig_info.items():
                    content.append(f"│  {key}: {value}")
                if i < len(hijacklib_data['ExpectedSignatureInformation']):
                    content.append("│")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if hijacklib_data.get('ExpectedVersionInformation'):
        content.append("┌─ <b>Expected Version Information</b>")
        for ver_info in hijacklib_data['ExpectedVersionInformation']:
            if isinstance(ver_info, dict):
                for key, value in ver_info.items():
                    content.append(f"│  {key}: {value}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if hijacklib_data.get('VulnerableExecutables'):
        content.append("┌─ <b>Vulnerable Executables</b>")
        for i, vuln_exe in enumerate(hijacklib_data['VulnerableExecutables'], 1):
            if isinstance(vuln_exe, dict):
                content.append(f"│")
                content.append(f"│  [{i}] Executable Details:")
                content.append(f"│  ┌─ Path: {vuln_exe.get('Path', 'N/A')}")
                content.append(f"│  ├─ Type: {vuln_exe.get('Type', 'N/A')}")
                
                if vuln_exe.get('SHA256'):
                    sha256_list = vuln_exe['SHA256'] if isinstance(vuln_exe['SHA256'], list) else [vuln_exe['SHA256']]
                    if len(sha256_list) == 1:
                        content.append(f"│  ├─ SHA256: {sha256_list[0]}")
                    else:
                        content.append(f"│  ├─ SHA256:")
                        for sha in sha256_list:
                            content.append(f"│  │    • {sha}")
                
                if vuln_exe.get('ExpectedSignatureInformation'):
                    content.append(f"│  ├─ Expected Signature Information:")
                    for sig_info in vuln_exe['ExpectedSignatureInformation']:
                        if isinstance(sig_info, dict):
                            for key, value in sig_info.items():
                                content.append(f"│  │    {key}: {value}")
                        else:
                            content.append(f"│  │    • {sig_info}")
                
                if vuln_exe.get('ExpectedVersionInformation'):
                    content.append(f"│  └─ Expected Version Information:")
                    for ver_info in vuln_exe['ExpectedVersionInformation']:
                        if isinstance(ver_info, dict):
                            for key, value in ver_info.items():
                                content.append(f"│       {key}: {value}")
                else:
                    content.append(f"│  └")
            else:
                content.append(f"│  • {vuln_exe}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if hijacklib_data.get('Resources'):
        content.append("┌─ <b>Resources</b>")
        for resource in hijacklib_data['Resources']:
            content.append(f"│  • {resource}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if hijacklib_data.get('Acknowledgements'):
        content.append("┌─ <b>Acknowledgements</b>")
        for ack in hijacklib_data['Acknowledgements']:
            if isinstance(ack, dict):
                name = ack.get('Name', 'N/A')
                twitter = ack.get('Twitter', '')
                if twitter:
                    content.append(f"│  • {name} ({twitter})")
                else:
                    content.append(f"│  • {name}")
            else:
                content.append(f"│  • {ack}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    content.append("┌─ <b>Metadata</b>")
    content.append(f"│  File: {hijacklib_data.get('file', 'N/A')}")
    content.append(f"│  Path: {hijacklib_data.get('file_path', 'N/A')}")
    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
    html_content = "\n".join(content).replace("\n", "<br>")
    text_area.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>{html_content}</pre>")
    layout.addWidget(text_area)
    
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet(styles.BUTTON_GREEN_INLINE)
    close_button.clicked.connect(detail_dialog.close)
    
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    layout.addLayout(button_layout)
    
    detail_dialog.exec()

NO_DATA_MSG = "No data found. Please click 'Download Updates' to download the latest files."


def display_hijacklibs_kb(parent, db_path):
    global HIJACKLIBS_WINDOW
    if HIJACKLIBS_WINDOW is not None:
        HIJACKLIBS_WINDOW.activateWindow()
        HIJACKLIBS_WINDOW.raise_()
        return HIJACKLIBS_WINDOW
    data = load_hijacklibs_data()
    if not data:
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
    kb_window = QWidget(parent.window)
    kb_window.setWindowTitle("HijackLibs")
    kb_window.resize(1200, 800)
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    HIJACKLIBS_WINDOW = kb_window
    
    original_close_event = kb_window.closeEvent
    def custom_close_event(event):
        global HIJACKLIBS_WINDOW
        HIJACKLIBS_WINDOW = None
        if original_close_event:
            original_close_event(event)
    kb_window.closeEvent = custom_close_event
    
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    header_layout = QHBoxLayout()
    title_label = QLabel("HijackLibs")
    title_font = QFont()
    title_font.setBold(True)
    title_font.setPointSize(16)
    title_label.setFont(title_font)
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    main_layout.addLayout(header_layout)
    filter_frame = QWidget()
    filter_layout = QHBoxLayout(filter_frame)
    filter_layout.setContentsMargins(0, 5, 0, 5)
    
    search_label = QLabel("Search:")
    search_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(search_label)
    
    search_textbox = QLineEdit()
    search_textbox.setPlaceholderText("Search by Name...")
    search_textbox.setFixedWidth(300)
    filter_layout.addWidget(search_textbox)
    
    filter_layout.addSpacing(10)
    
    vendor_label = QLabel("Vendor:")
    vendor_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(vendor_label)
    
    vendor_filter = QComboBox()
    vendor_filter.addItem("All")
    vendor_filter.setFixedWidth(200)
    filter_layout.addWidget(vendor_filter)
    
    filter_layout.addStretch()
    main_layout.addWidget(filter_frame)
    splitter = QSplitter(Qt.Horizontal)
    tree_view = QTreeView()
    tree_view.setRootIsDecorated(False)
    tree_view.setAlternatingRowColors(True)
    tree_view.setSelectionBehavior(QTreeView.SelectRows)
    tree_view.setSortingEnabled(True)
    tree_view.setStyleSheet(styles.TREE_VIEW_KB_STYLE)
    
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Name"])
    tree_view.setModel(model)
    tree_view.setColumnWidth(0, 210)
    
    splitter.addWidget(tree_view)
    detail_view = QTextEdit()
    detail_view.setReadOnly(True)
    detail_view.setFont(QFont("Consolas", 10) or QFont("Courier New", 10))
    detail_view.setStyleSheet(styles.DETAIL_VIEW_KB_STYLE)
    detail_view.setPlaceholderText("Select a hijacklib to view details...")
    splitter.addWidget(detail_view)
    
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    
    main_layout.addWidget(splitter, 1)
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://github.com/wietze/HijackLibs'>https://github.com/wietze/HijackLibs</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)
    
    full_data_store = []
    
    def filter_hijacklibs(search_text="", vendor_filter_text="All"):
        filtered = []
        try:
            hijacklibs_data = load_hijacklibs_data()
            if not hijacklibs_data:
                return []
            
            search_lower = search_text.strip().lower() if search_text else None
            for hijacklib in hijacklibs_data:
                if search_lower is not None:
                    name = hijacklib.get("Name", hijacklib.get("name", ""))
                    if search_lower not in str(name).lower():
                        continue
                if vendor_filter_text != "All":
                    vendor = hijacklib.get('Vendor', '')
                    if vendor != vendor_filter_text:
                        continue
                
                filtered.append(hijacklib)
        except Exception as e:
            logger.error("Error filtering hijacklibs: %s", e)
        return filtered
    
    def populate_tree(search_text="", vendor_filter_text="All"):
        nonlocal full_data_store
        model.removeRows(0, model.rowCount())
        full_data_store.clear()
        
        try:
            filtered_data = filter_hijacklibs(search_text, vendor_filter_text)
            
            if not filtered_data:
                if not load_hijacklibs_data():
                    QMessageBox.information(kb_window, "No HijackLibs Data", 
                        "No hijacklibs data found. Please ensure the data/hijacklib directory exists and contains YAML files.")
                    return
            for hijacklib in sorted(filtered_data, key=lambda x: x.get('Name', x.get('name', ''))):
                name = str(hijacklib.get('Name', hijacklib.get('name', '')))
                
                item = QStandardItem(name)
                model.appendRow(item)
                full_data_store.append(hijacklib)
            
            logger.info("Displayed %s hijacklibs, stored %s items for detailed view", len(filtered_data), len(full_data_store))
        except Exception as e:
            logger.error("Error populating tree: %s", e)
            QMessageBox.critical(kb_window, "Error", f"Failed to populate data: {e}")
    
    def update_display():
        search_text = search_textbox.text()
        vendor_filter_text = vendor_filter.currentText()
        populate_tree(search_text, vendor_filter_text)
    
    def on_item_selected(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                hijacklib_data = full_data_store[row]
                hijacklib_name = hijacklib_data.get("Name", hijacklib_data.get("name", "N/A"))
                content = []
                content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
                name_padding = max(0, DETAIL_LINE_WIDTH - (len(hijacklib_name) + 2))
                content.append(f"║  <b>{hijacklib_name}</b>" + " " * name_padding + "║")
                content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
                content.append("")
                vuln_executables = hijacklib_data.get("VulnerableExecutables", [])
                if vuln_executables:
                    exe_count = len(vuln_executables)
                    hijack_type = f"DLL Sideloading ({exe_count} EXE{'s' if exe_count > 1 else ''})"
                    content.append(f"┌─ <b>DLL Hijacking Type</b>")
                    content.append(f"│  {hijack_type}")
                    content.append("│")
                    content.append("│  Copy (and optionally rename) a vulnerable application alongside a")
                    content.append("│  malicious DLL to execute arbitrary code through the legitimate")
                    content.append("│  application.")
                    content.append("│")
                    content.append("│  MITRE ATT&CK®: T1574.001 - Hijack Execution Flow: DLL")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                content.append("┌─ <b>General Information</b>")
                if hijacklib_data.get('Vendor'):
                    content.append(f"│  DLL Vendor: {hijacklib_data['Vendor']}")
                if hijacklib_data.get('Author'):
                    content.append(f"│  Author: {hijacklib_data['Author']}")
                if hijacklib_data.get('Created'):
                    content.append(f"│  Created: {hijacklib_data['Created']}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                content.append("")
                if hijacklib_data.get('ExpectedLocations'):
                    content.append("┌─ <b>Expected Locations</b>")
                    for location in hijacklib_data['ExpectedLocations']:
                        content.append(f"│  • {location}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if hijacklib_data.get('ExpectedSignatureInformation'):
                    content.append("┌─ <b>Expected Signature Information</b>")
                    for i, sig_info in enumerate(hijacklib_data['ExpectedSignatureInformation'], 1):
                        if isinstance(sig_info, dict):
                            for key, value in sig_info.items():
                                content.append(f"│  {key}: {value}")
                            if i < len(hijacklib_data['ExpectedSignatureInformation']):
                                content.append("│")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if hijacklib_data.get('ExpectedVersionInformation'):
                    content.append("┌─ <b>Expected Version Information</b>")
                    for ver_info in hijacklib_data['ExpectedVersionInformation']:
                        if isinstance(ver_info, dict):
                            for key, value in ver_info.items():
                                content.append(f"│  {key}: {value}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if hijacklib_data.get('VulnerableExecutables'):
                    content.append("┌─ <b>Vulnerable Executables</b>")
                    for i, vuln_exe in enumerate(hijacklib_data['VulnerableExecutables'], 1):
                        if isinstance(vuln_exe, dict):
                            content.append(f"│")
                            content.append(f"│  [{i}] Executable Details:")
                            content.append(f"│  ┌─ Path: {vuln_exe.get('Path', 'N/A')}")
                            content.append(f"│  ├─ Type: {vuln_exe.get('Type', 'N/A')}")
                            
                            if vuln_exe.get('SHA256'):
                                sha256_list = vuln_exe['SHA256'] if isinstance(vuln_exe['SHA256'], list) else [vuln_exe['SHA256']]
                                if len(sha256_list) == 1:
                                    content.append(f"│  ├─ SHA256: {sha256_list[0]}")
                                else:
                                    content.append(f"│  ├─ SHA256:")
                                    for sha in sha256_list:
                                        content.append(f"│  │    • {sha}")
                            
                            if vuln_exe.get('ExpectedSignatureInformation'):
                                content.append(f"│  ├─ Expected Signature Information:")
                                for sig_info in vuln_exe['ExpectedSignatureInformation']:
                                    if isinstance(sig_info, dict):
                                        for key, value in sig_info.items():
                                            content.append(f"│  │    {key}: {value}")
                                    else:
                                        content.append(f"│  │    • {sig_info}")
                            
                            if vuln_exe.get('ExpectedVersionInformation'):
                                content.append(f"│  └─ Expected Version Information:")
                                for ver_info in vuln_exe['ExpectedVersionInformation']:
                                    if isinstance(ver_info, dict):
                                        for key, value in ver_info.items():
                                            content.append(f"│       {key}: {value}")
                            else:
                                content.append(f"│  └")
                        else:
                            content.append(f"│  • {vuln_exe}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if hijacklib_data.get('Resources'):
                    content.append("┌─ <b>Resources</b>")
                    for resource in hijacklib_data['Resources']:
                        content.append(f"│  • {resource}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if hijacklib_data.get('Acknowledgements'):
                    content.append("┌─ <b>Acknowledgements</b>")
                    for ack in hijacklib_data['Acknowledgements']:
                        if isinstance(ack, dict):
                            name = ack.get('Name', 'N/A')
                            twitter = ack.get('Twitter', '')
                            if twitter:
                                content.append(f"│  • {name} ({twitter})")
                            else:
                                content.append(f"│  • {name}")
                        else:
                            content.append(f"│  • {ack}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                content.append("┌─ <b>Metadata</b>")
                content.append(f"│  File: {hijacklib_data.get('file', 'N/A')}")
                content.append(f"│  Path: {hijacklib_data.get('file_path', 'N/A')}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                html_content = "\n".join(content).replace("\n", "<br>")
                detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>{html_content}</pre>")
            else:
                detail_view.clear()
        except Exception as e:
            logger.error("Error in selection handler: %s", e)
            detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>Error loading hijacklib details: {e}</pre>")
    
    def on_item_double_clicked(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                hijacklib_data = full_data_store[row]
                show_detailed_view(kb_window, hijacklib_data)
        except Exception as e:
            logger.error("Error in double-click handler: %s", e)
            QMessageBox.warning(kb_window, "Error", f"Failed to open detailed view: {e}")
    
    tree_view.selectionModel().currentChanged.connect(on_item_selected)
    tree_view.doubleClicked.connect(on_item_double_clicked)
    search_textbox.textChanged.connect(update_display)
    vendor_filter.currentTextChanged.connect(update_display)
    try:
        hijacklibs_data = load_hijacklibs_data()
        if hijacklibs_data:
            vendors = sorted(set(h.get('Vendor', '') for h in hijacklibs_data if h.get('Vendor')))
            vendor_filter.addItems(vendors)
    except Exception as e:
        logger.error("Error populating vendor filter: %s", e)
    populate_tree()
    
    kb_window.show()
    return kb_window

