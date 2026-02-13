"""
LOLDrivers (Living Off The Land Drivers) knowledge-base window for Kanvas: loads
driver data from data/microsoft/drivers.json, provides search and detail view.
Cross-platform (Windows, macOS, Linux). Revised on 01/02/2026 by Jinto Antony
"""

import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
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

LOLDRIVERS_WINDOW = None
LOLDRIVERS_DATA_CACHE = None
DETAIL_LINE_WIDTH = 78
DETAIL_BORDER_WIDTH = 77


def load_loldrivers_data():
    global LOLDRIVERS_DATA_CACHE
    if LOLDRIVERS_DATA_CACHE is not None:
        return LOLDRIVERS_DATA_CACHE
    loldrivers_data = []
    base_dir = Path(__file__).parent.parent.parent
    drivers_file = base_dir / "data" / "microsoft" / "drivers.json"
    drivers_file_path = drivers_file
    if not drivers_file_path.exists():
        microsoft_dir = base_dir / "data" / "microsoft"
        if microsoft_dir.exists():
            for f in microsoft_dir.iterdir():
                if f.name.lower() == "drivers.json":
                    drivers_file_path = f
                    break
    try:
        if not drivers_file_path.exists():
            logger.error("Drivers file not found: %s", drivers_file)
            logger.warning("Drivers file does not exist. Please ensure the data/microsoft/drivers.json file exists.")
            return []
        with open(drivers_file_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            
        if not isinstance(data, list):
            logger.error("Drivers JSON file does not contain an array")
            return []
        
        for driver_entry in data:
            if not isinstance(driver_entry, dict):
                continue
            tags = driver_entry.get('Tags', [])
            driver_name = tags[0] if tags and len(tags) > 0 else 'Unknown'
            commands_obj = driver_entry.get('Commands', {})
            
            loldrivers_data.append({
                'name': driver_name,
                'tags': tags,
                'verified': driver_entry.get('Verified', ''),
                'author': driver_entry.get('Author', ''),
                'created': driver_entry.get('Created', ''),
                'mitre_id': driver_entry.get('MitreID', ''),
                'category': driver_entry.get('Category', ''),
                'commands': commands_obj,
                'resources': driver_entry.get('Resources', []),
                'detection': driver_entry.get('Detection', []),
                'acknowledgement': driver_entry.get('Acknowledgement', {}),
                'known_vulnerable_samples': driver_entry.get('KnownVulnerableSamples', []),
                'id': driver_entry.get('Id', '')
            })
        
        logger.info("Loaded %s drivers from %s", len(loldrivers_data), drivers_file_path)
    except json.JSONDecodeError as e:
        logger.error("JSON parse error in %s: %s", drivers_file_path, e)
        return []
    except Exception as e:
        logger.error("Error loading drivers data: %s", e)
        return []
    
    LOLDRIVERS_DATA_CACHE = loldrivers_data
    return loldrivers_data

def show_detailed_view(parent, item_data):
    detail_dialog = QDialog(parent)
    driver_name = item_data.get('name', 'Unknown')
    detail_dialog.setWindowTitle(f"LOLDrivers Details - {driver_name}")
    detail_dialog.resize(900, 700)
    detail_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    layout = QVBoxLayout(detail_dialog)
    
    title_label = QLabel(f"LOLDrivers Details - {driver_name}")
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
    
    content = []
    content.append("=" * 80)
    content.append(f"LOLDRIVERS DETAILS: {driver_name}")
    content.append("=" * 80)
    content.append("")
    content.append("BASIC INFORMATION:")
    content.append("-" * 40)
    content.append(f"Name: {driver_name}")
    if item_data.get('category'):
        content.append(f"Category: {item_data['category']}")
    if item_data.get('verified'):
        content.append(f"Verified: {item_data['verified']}")
    if item_data.get('author'):
        content.append(f"Author: {item_data['author']}")
    if item_data.get('created'):
        content.append(f"Created: {item_data['created']}")
    if item_data.get('mitre_id'):
        content.append(f"MITRE ID: {item_data['mitre_id']}")
    if item_data.get('tags'):
        content.append(f"Tags: {', '.join(item_data['tags'])}")
    content.append("")
    commands_obj = item_data.get('commands', {})
    if commands_obj and isinstance(commands_obj, dict):
        content.append("COMMANDS:")
        content.append("-" * 40)
        if commands_obj.get('Command'):
            content.append(f"  <span style='color: red; font-weight: bold;'>Command:</span> {commands_obj.get('Command', 'N/A')}")
        if commands_obj.get('Description'):
            content.append(f"  Description: {commands_obj.get('Description', 'N/A')}")
        if commands_obj.get('Usecase'):
            content.append(f"  Usecase: {commands_obj.get('Usecase', 'N/A')}")
        if commands_obj.get('Privileges'):
            content.append(f"  Privileges: {commands_obj.get('Privileges', 'N/A')}")
        if commands_obj.get('OperatingSystem'):
            content.append(f"  Operating System: {commands_obj.get('OperatingSystem', 'N/A')}")
        content.append("")
    samples = item_data.get('known_vulnerable_samples', [])
    if samples:
        content.append("KNOWN VULNERABLE SAMPLES:")
        content.append("-" * 40)
        for i, sample in enumerate(samples, 1):
            content.append(f"Sample {i}:")
            if isinstance(sample, dict):
                if sample.get('Filename'):
                    content.append(f"  Filename: {sample['Filename']}")
                if sample.get('SHA256'):
                    content.append(f"  SHA256: {sample['SHA256']}")
                if sample.get('MD5'):
                    content.append(f"  MD5: {sample['MD5']}")
                if sample.get('SHA1'):
                    content.append(f"  SHA1: {sample['SHA1']}")
                if sample.get('Company'):
                    content.append(f"  Company: {sample['Company']}")
                if sample.get('Publisher'):
                    content.append(f"  Publisher: {sample['Publisher']}")
                if sample.get('Product'):
                    content.append(f"  Product: {sample['Product']}")
                if sample.get('FileVersion'):
                    content.append(f"  File Version: {sample['FileVersion']}")
                if sample.get('ProductVersion'):
                    content.append(f"  Product Version: {sample['ProductVersion']}")
                if sample.get('MachineType'):
                    content.append(f"  Machine Type: {sample['MachineType']}")
                if sample.get('CreationTimestamp'):
                    content.append(f"  Creation Timestamp: {sample['CreationTimestamp']}")
                if sample.get('Signature'):
                    content.append(f"  Signature: {sample['Signature']}")
                if sample.get('LoadsDespiteHVCI'):
                    content.append(f"  Loads Despite HVCI: {sample['LoadsDespiteHVCI']}")
                if sample.get('Imphash'):
                    content.append(f"  Imphash: {sample['Imphash']}")
                if sample.get('Authentihash'):
                    auth_hash = sample.get('Authentihash', {})
                    if isinstance(auth_hash, dict):
                        if auth_hash.get('SHA256'):
                            content.append(f"  Authentihash SHA256: {auth_hash['SHA256']}")
            content.append("")
        content.append("")
    if item_data.get('detection'):
        content.append("DETECTION RULES:")
        content.append("-" * 40)
        for i, det in enumerate(item_data['detection'], 1):
            content.append(f"Rule {i}:")
            if isinstance(det, dict):
                for key, value in det.items():
                    content.append(f"  {key}: {value}")
            else:
                content.append(f"  {det}")
            content.append("")
        content.append("")
    if item_data.get('resources'):
        content.append("RESOURCES:")
        content.append("-" * 40)
        for i, res in enumerate(item_data['resources'], 1):
            if isinstance(res, dict):
                content.append(f"  {i}. {res.get('Link', 'N/A')}")
            else:
                content.append(f"  {i}. {res}")
        content.append("")
    ack = item_data.get('acknowledgement', {})
    if ack and isinstance(ack, dict):
        person = ack.get('Person', '')
        handle = ack.get('Handle', '')
        if person or handle:
            content.append("ACKNOWLEDGEMENTS:")
            content.append("-" * 40)
            if person:
                content.append(f"  Person: {person}")
            if handle:
                content.append(f"  Handle: {handle}")
            content.append("")
    
    content.append("=" * 80)
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


def display_loldrivers_kb(parent, db_path):
    global LOLDRIVERS_WINDOW
    if LOLDRIVERS_WINDOW is not None:
        LOLDRIVERS_WINDOW.activateWindow()
        LOLDRIVERS_WINDOW.raise_()
        return LOLDRIVERS_WINDOW
    data = load_loldrivers_data()
    if not data:
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
    kb_window = QWidget(parent.window)
    kb_window.setWindowTitle("LOLDrivers - Living Off The Land Drivers")
    kb_window.resize(1000, 800)
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    LOLDRIVERS_WINDOW = kb_window
    
    original_close_event = kb_window.closeEvent
    def custom_close_event(event):
        global LOLDRIVERS_WINDOW
        LOLDRIVERS_WINDOW = None
        if original_close_event:
            original_close_event(event)
    kb_window.closeEvent = custom_close_event
    
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    header_layout = QHBoxLayout()
    title_label = QLabel("LOLDrivers - Living Off The Land Drivers")
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
    
    search_label = QLabel("Search Name:")
    search_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(search_label)
    
    search_textbox = QLineEdit()
    search_textbox.setPlaceholderText("Search by driver name, SHA256, SHA1, or MD5...")
    search_textbox.setFixedWidth(300)
    filter_layout.addWidget(search_textbox)
    
    filter_layout.addSpacing(10)
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
    tree_view.setColumnWidth(0, 300)
    
    splitter.addWidget(tree_view)
    detail_view = QTextEdit()
    detail_view.setReadOnly(True)
    detail_view.setFont(QFont("Consolas", 10) or QFont("Courier New", 10))
    detail_view.setStyleSheet(styles.DETAIL_VIEW_KB_STYLE)
    detail_view.setPlaceholderText("Select a driver to view details...")
    splitter.addWidget(detail_view)
    
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    
    main_layout.addWidget(splitter, 1)
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://www.loldrivers.io'>loldrivers.io</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)
    
    full_data_store = []
    
    def filter_drivers(search_term=""):
        filtered = []
        try:
            drivers_data = load_loldrivers_data()
            if not drivers_data:
                return []
            
            if not search_term.strip():
                return drivers_data
            search_lower = search_term.strip().lower()
            for item in drivers_data:
                name_match = search_lower in item.get("name", "").lower()
                hash_match = False
                samples = item.get('known_vulnerable_samples', [])
                for sample in samples:
                    if isinstance(sample, dict):
                        if sample.get('SHA256') and search_lower in sample.get('SHA256', '').lower():
                            hash_match = True
                            break
                        if sample.get('SHA1') and search_lower in sample.get('SHA1', '').lower():
                            hash_match = True
                            break
                        if sample.get('MD5') and search_lower in sample.get('MD5', '').lower():
                            hash_match = True
                            break
                        auth_hash = sample.get('Authentihash', {})
                        if isinstance(auth_hash, dict):
                            if auth_hash.get('SHA256') and search_lower in auth_hash.get('SHA256', '').lower():
                                hash_match = True
                                break
                            if auth_hash.get('SHA1') and search_lower in auth_hash.get('SHA1', '').lower():
                                hash_match = True
                                break
                            if auth_hash.get('MD5') and search_lower in auth_hash.get('MD5', '').lower():
                                hash_match = True
                                break
                
                if name_match or hash_match:
                    filtered.append(item)
        except Exception as e:
            logger.error("Error filtering drivers: %s", e)
        return filtered
    
    def populate_tree(search_term=""):
        nonlocal full_data_store
        model.removeRows(0, model.rowCount())
        full_data_store.clear()
        
        try:
            filtered_data = filter_drivers(search_term)
            
            if not filtered_data:
                if not load_loldrivers_data():
                    QMessageBox.information(kb_window, "No LOLDrivers Data", 
                        "No LOLDrivers data found. Please ensure the data/microsoft/drivers.json file exists.")
                return
            
            for item in sorted(filtered_data, key=lambda x: x.get('name', '')):
                name = str(item.get('name', ''))
                tree_item = QStandardItem(name)
                model.appendRow(tree_item)
                full_data_store.append(item)
            
            logger.info("Displayed %s drivers, stored %s items for detailed view", len(filtered_data), len(full_data_store))
        except Exception as e:
            logger.error("Error populating tree: %s", e)
            QMessageBox.critical(kb_window, "Error", f"Failed to populate data: {e}")
    
    def search_tools():
        search_term = search_textbox.text()
        populate_tree(search_term)
    
    def on_item_selected(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                item_data = full_data_store[row]
                driver_name = item_data.get("name", "N/A")
                content = []
                content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
                name_padding = max(0, DETAIL_LINE_WIDTH - (len(driver_name) + 2))
                content.append(f"║  <b>{driver_name}</b>" + " " * name_padding + "║")
                content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
                content.append("")
                content.append("┌─ <b>Basic Information</b>")
                if item_data.get('category'):
                    content.append(f"│  Category: {item_data['category']}")
                if item_data.get('verified'):
                    content.append(f"│  Verified: {item_data['verified']}")
                if item_data.get('author'):
                    content.append(f"│  Author: {item_data['author']}")
                if item_data.get('created'):
                    content.append(f"│  Created: {item_data['created']}")
                if item_data.get('mitre_id'):
                    content.append(f"│  MITRE ID: {item_data['mitre_id']}")
                if item_data.get('tags'):
                    content.append(f"│  Tags: {', '.join(item_data['tags'])}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                content.append("")
                commands_obj = item_data.get('commands', {})
                if commands_obj and isinstance(commands_obj, dict):
                    content.append("┌─ <b>Commands</b>")
                    content.append(f"│  ┌─ <span style='color: red; font-weight: bold;'>Command:</span> {commands_obj.get('Command', 'N/A')}")
                    
                    has_desc = bool(commands_obj.get('Description'))
                    has_usecase = bool(commands_obj.get('Usecase'))
                    has_privileges = bool(commands_obj.get('Privileges'))
                    has_os = bool(commands_obj.get('OperatingSystem'))
                    
                    has_any = has_desc or has_usecase or has_privileges or has_os
                    
                    if has_desc:
                        connector = "├" if (has_usecase or has_privileges or has_os) else "└"
                        content.append(f"│  {connector}─ Description: {commands_obj['Description']}")
                    
                    if has_usecase:
                        connector = "├" if (has_privileges or has_os) else "└"
                        content.append(f"│  {connector}─ Usecase: {commands_obj['Usecase']}")
                    
                    if has_privileges:
                        connector = "├" if has_os else "└"
                        content.append(f"│  {connector}─ Privileges: {commands_obj['Privileges']}")
                    
                    if has_os:
                        content.append(f"│  └─ Operating System: {commands_obj['OperatingSystem']}")
                    elif not has_any:
                        content.append(f"│  └")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                samples = item_data.get('known_vulnerable_samples', [])
                if samples:
                    content.append("┌─ <b>Known Vulnerable Samples</b>")
                    for i, sample in enumerate(samples, 1):
                        content.append(f"│")
                        content.append(f"│  [{i}] Sample Details:")
                        if isinstance(sample, dict):
                            if sample.get('Filename'):
                                content.append(f"│  ┌─ Filename: {sample['Filename']}")
                            
                            has_sha256 = bool(sample.get('SHA256'))
                            has_md5 = bool(sample.get('MD5'))
                            has_sha1 = bool(sample.get('SHA1'))
                            has_company = bool(sample.get('Company'))
                            has_publisher = bool(sample.get('Publisher'))
                            has_product = bool(sample.get('Product'))
                            has_version = bool(sample.get('FileVersion') or sample.get('ProductVersion'))
                            has_machine = bool(sample.get('MachineType'))
                            has_timestamp = bool(sample.get('CreationTimestamp'))
                            has_signature = bool(sample.get('Signature'))
                            has_hvci = bool(sample.get('LoadsDespiteHVCI'))
                            has_imphash = bool(sample.get('Imphash'))
                            
                            has_any = has_sha256 or has_md5 or has_sha1 or has_company or has_publisher or has_product or has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash
                            
                            if has_sha256:
                                connector = "├" if (has_md5 or has_sha1 or has_company or has_publisher or has_product or has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ SHA256: {sample['SHA256']}")
                            
                            if has_md5:
                                connector = "├" if (has_sha1 or has_company or has_publisher or has_product or has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ MD5: {sample['MD5']}")
                            
                            if has_sha1:
                                connector = "├" if (has_company or has_publisher or has_product or has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ SHA1: {sample['SHA1']}")
                            
                            if has_company:
                                connector = "├" if (has_publisher or has_product or has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ Company: {sample['Company']}")
                            
                            if has_publisher:
                                connector = "├" if (has_product or has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ Publisher: {sample['Publisher']}")
                            
                            if has_product:
                                connector = "├" if (has_version or has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ Product: {sample['Product']}")
                            
                            if has_version:
                                connector = "├" if (has_machine or has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                version_info = []
                                if sample.get('FileVersion'):
                                    version_info.append(f"File: {sample['FileVersion']}")
                                if sample.get('ProductVersion'):
                                    version_info.append(f"Product: {sample['ProductVersion']}")
                                content.append(f"│  {connector}─ Version: {', '.join(version_info)}")
                            
                            if has_machine:
                                connector = "├" if (has_timestamp or has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ Machine Type: {sample['MachineType']}")
                            
                            if has_timestamp:
                                connector = "├" if (has_signature or has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ Creation Timestamp: {sample['CreationTimestamp']}")
                            
                            if has_signature:
                                connector = "├" if (has_hvci or has_imphash) else "└"
                                content.append(f"│  {connector}─ Signature: {sample['Signature']}")
                            
                            if has_hvci:
                                connector = "├" if has_imphash else "└"
                                content.append(f"│  {connector}─ Loads Despite HVCI: {sample['LoadsDespiteHVCI']}")
                            
                            if has_imphash:
                                content.append(f"│  └─ Imphash: {sample['Imphash']}")
                            elif not has_any:
                                content.append(f"│  └")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if item_data.get('detection'):
                    content.append("┌─ <b>Detection Rules</b>")
                    for i, det in enumerate(item_data['detection'], 1):
                        content.append(f"│")
                        content.append(f"│  [{i}] Rule Details:")
                        if isinstance(det, dict):
                            for key, value in det.items():
                                content.append(f"│    • {key}: {value}")
                        else:
                            content.append(f"│    • {det}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if item_data.get('resources'):
                    content.append("┌─ <b>Resources</b>")
                    for i, res in enumerate(item_data['resources'], 1):
                        if isinstance(res, dict):
                            link = res.get('Link', str(res))
                        else:
                            link = str(res)
                        content.append(f"│  {i}. {link}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                ack = item_data.get('acknowledgement', {})
                if ack and isinstance(ack, dict):
                    person = ack.get('Person', '')
                    handle = ack.get('Handle', '')
                    if person or handle:
                        content.append("┌─ <b>Acknowledgements</b>")
                        if person:
                            content.append(f"│  • Person: {person}")
                        if handle:
                            content.append(f"│    Handle: {handle}")
                        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                        content.append("")
                html_content = "\n".join(content).replace("\n", "<br>")
                detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>{html_content}</pre>")
            else:
                detail_view.clear()
        except Exception as e:
            logger.error("Error in selection handler: %s", e)
            detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>Error loading driver details: {e}</pre>")
    
    def on_item_double_clicked(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                item_data = full_data_store[row]
                show_detailed_view(kb_window, item_data)
        except Exception as e:
            logger.error("Error in double-click handler: %s", e)
            QMessageBox.warning(kb_window, "Error", f"Failed to open detailed view: {e}")
    
    tree_view.selectionModel().currentChanged.connect(on_item_selected)
    tree_view.doubleClicked.connect(on_item_double_clicked)
    search_textbox.textChanged.connect(search_tools)
    populate_tree("")
    
    kb_window.show()
    return kb_window

