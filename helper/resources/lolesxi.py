"""
LOLESXi (Living Off The Land ESXi) knowledge-base window for Kanvas: loads
markdown/YAML data from data/linux/lolesxi, provides search and detail view.
Cross-platform (Windows, macOS, Linux). Revised on 01/02/2026 by Jinto Antony
"""

import logging
from pathlib import Path

import yaml
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

LOLESXI_WINDOW = None
LOLESXI_DATA_CACHE = None
DETAIL_LINE_WIDTH = 78
DETAIL_BORDER_WIDTH = 77


def load_lolesxi_data():
    global LOLESXI_DATA_CACHE
    if LOLESXI_DATA_CACHE is not None:
        return LOLESXI_DATA_CACHE
    lolesxi_data = []
    base_dir = Path(__file__).parent.parent.parent
    lolesxi_dir = base_dir / "data" / "linux" / "lolesxi"
    lolesxi_dir_path = lolesxi_dir
    if not lolesxi_dir_path.exists():
        linux_dir = base_dir / "data" / "linux"
        if linux_dir.exists():
            for subdir in linux_dir.iterdir():
                if subdir.is_dir() and subdir.name.lower() == "lolesxi":
                    lolesxi_dir_path = subdir
                    break
    try:
        if not lolesxi_dir_path.exists():
            logger.error("LOLESXi directory not found: %s", lolesxi_dir)
            logger.warning("LOLESXi directory does not exist. Please ensure the data/linux/lolesxi directory exists.")
            return []
        md_files = [f for f in lolesxi_dir_path.iterdir() if f.is_file() and f.suffix.lower() == ".md"]
        logger.info("Found %s markdown files in LOLESXi directory", len(md_files))
        if not md_files:
            logger.warning("No markdown files found in LOLESXi directory.")
            return []
        for md_file in md_files:
            try:
                with open(md_file, "r", encoding="utf-8") as fp:
                    content = fp.read()
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        yaml_content = parts[1].strip()
                        data = yaml.safe_load(yaml_content)
                        
                        if data and 'Name' in data:
                            commands = data.get('Commands', [])
                            first_command = commands[0] if commands else {}
                            lolesxi_data.append({
                                'name': data.get('Name', ''),
                                'description': data.get('Description', ''),
                                'author': data.get('Author', ''),
                                'created': data.get('Created', ''),
                                'commands': commands,
                                'category': first_command.get('Category', 'Unknown'),
                                'mitre_id': first_command.get('MitreID', ''),
                                'os': first_command.get('OperatingSystem', ''),
                                'privileges': first_command.get('Privileges', ''),
                                'full_path': data.get('Full_Path', []),
                                'detection': data.get('Detection', []),
                                'code_sample': data.get('Code_Sample', []),
                                'atomic_tests': data.get('AtomicTests', []),
                                'resources': data.get('Resources', []),
                                'acknowledgement': data.get('Acknowledgement', []),
                                'file': md_file.name
                            })
            except Exception as e:
                logger.error("Error loading %s: %s", md_file.name, e)
                continue
    except Exception as e:
        logger.error("Error loading LOLESXi data: %s", e)
    
    LOLESXI_DATA_CACHE = lolesxi_data
    return lolesxi_data

def show_detailed_view(parent, item_data):
    detail_dialog = QDialog(parent)
    tool_name = item_data.get('name', 'Unknown')
    detail_dialog.setWindowTitle(f"LOLESXi Details - {tool_name}")
    detail_dialog.resize(900, 700)
    detail_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    layout = QVBoxLayout(detail_dialog)
    
    title_label = QLabel(f"LOLESXi Details - {tool_name}")
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
    content.append(f"LOLESXi DETAILS: {item_data.get('name', 'Unknown')}")
    content.append("=" * 80)
    content.append("")
    content.append("BASIC INFORMATION:")
    content.append("-" * 40)
    content.append(f"Name: {item_data.get('name', 'N/A')}")
    content.append(f"Description: {item_data.get('description', 'N/A')}")
    content.append(f"Author: {item_data.get('author', 'N/A')}")
    content.append(f"Created: {item_data.get('created', 'N/A')}")
    content.append(f"Category: {item_data.get('category', 'N/A')}")
    content.append(f"MITRE ID: {item_data.get('mitre_id', 'N/A')}")
    content.append(f"Operating System: {item_data.get('os', 'N/A')}")
    content.append(f"Privileges: {item_data.get('privileges', 'N/A')}")
    content.append("")
    
    if item_data.get('commands'):
        content.append("COMMANDS:")
        content.append("-" * 40)
        for i, cmd in enumerate(item_data.get('commands', []), 1):
            content.append(f"Command {i}:")
            content.append(f"  <span style='color: red; font-weight: bold;'>Command:</span> {cmd.get('Command', 'N/A')}")
            content.append(f"  Description: {cmd.get('Description', 'N/A')}")
            content.append(f"  Usecase: {cmd.get('Usecase', 'N/A')}")
            content.append(f"  Category: {cmd.get('Category', 'N/A')}")
            content.append(f"  Privileges: {cmd.get('Privileges', 'N/A')}")
            content.append(f"  MITRE ID: {cmd.get('MitreID', 'N/A')}")
            content.append(f"  OS: {cmd.get('OperatingSystem', 'N/A')}")
            if cmd.get('ProceduralExamples'):
                content.append(f"  Procedural Examples:")
                for example in cmd.get('ProceduralExamples', []):
                    content.append(f"    - {example}")
            if cmd.get('Tags'):
                tags = cmd.get('Tags', [])
                if isinstance(tags, list):
                    tag_strings = []
                    for tag in tags:
                        if isinstance(tag, dict):
                            tag_strings.append(f"{list(tag.keys())[0]}: {list(tag.values())[0]}")
                        else:
                            tag_strings.append(str(tag))
                    content.append(f"  Tags: {', '.join(tag_strings)}")
                else:
                    content.append(f"  Tags: {tags}")
            content.append("")
        content.append("")
    
    if item_data.get('full_path'):
        content.append("FULL PATHS:")
        content.append("-" * 40)
        for path_info in item_data.get('full_path', []):
            path = path_info.get('Path', path_info) if isinstance(path_info, dict) else path_info
            content.append(f"  {path}")
        content.append("")
    
    if item_data.get('detection'):
        content.append("DETECTION RULES:")
        content.append("-" * 40)
        for i, det in enumerate(item_data.get('detection', []), 1):
            content.append(f"Rule {i}:")
            if isinstance(det, dict):
                for key, value in det.items():
                    content.append(f"  {key}: {value}")
            else:
                content.append(f"  {det}")
            content.append("")
        content.append("")
    
    if item_data.get('atomic_tests'):
        content.append("ATOMIC TESTS:")
        content.append("-" * 40)
        for i, test in enumerate(item_data.get('atomic_tests', []), 1):
            if isinstance(test, dict):
                content.append(f"  {i}. {test.get('Link', 'N/A')}")
            else:
                content.append(f"  {i}. {test}")
        content.append("")
    
    if item_data.get('resources'):
        content.append("RESOURCES:")
        content.append("-" * 40)
        for i, res in enumerate(item_data.get('resources', []), 1):
            if isinstance(res, dict):
                content.append(f"  {i}. {res.get('Link', 'N/A')}")
            else:
                content.append(f"  {i}. {res}")
        content.append("")
    
    if item_data.get('acknowledgement'):
        content.append("ACKNOWLEDGEMENTS:")
        content.append("-" * 40)
        for ack in item_data.get('acknowledgement', []):
            if isinstance(ack, dict):
                person = ack.get('Person', 'N/A')
                handle = ack.get('Handle', 'N/A')
                content.append(f"  Person: {person}")
                if handle:
                    content.append(f"  Handle: {handle}")
            else:
                content.append(f"  {ack}")
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


def display_lolesxi_kb(parent, db_path):
    global LOLESXI_WINDOW
    if LOLESXI_WINDOW is not None:
        LOLESXI_WINDOW.activateWindow()
        LOLESXI_WINDOW.raise_()
        return LOLESXI_WINDOW
    data = load_lolesxi_data()
    if not data:
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
    kb_window = QWidget(parent.window)
    kb_window.setWindowTitle("LOLESXi - Living Off The Land ESXi")
    kb_window.resize(1000, 800)
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    LOLESXI_WINDOW = kb_window
    
    original_close_event = kb_window.closeEvent
    def custom_close_event(event):
        global LOLESXI_WINDOW
        LOLESXI_WINDOW = None
        if original_close_event:
            original_close_event(event)
    kb_window.closeEvent = custom_close_event
    
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    header_layout = QHBoxLayout()
    title_label = QLabel("LOLESXi - Living Off The Land ESXi")
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
    search_textbox.setPlaceholderText("Enter tool name to search...")
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
    detail_view.setPlaceholderText("Select a tool to view details...")
    splitter.addWidget(detail_view)
    
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    
    main_layout.addWidget(splitter, 1)
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://lolesxi-project.github.io/LOLESXi/'>https://lolesxi-project.github.io/LOLESXi/</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)
    
    full_data_store = []
    
    def filter_lolesxi(search_term=""):
        filtered = []
        try:
            lolesxi_data = load_lolesxi_data()
            if not lolesxi_data:
                return []
            search_lower = search_term.strip().lower() if search_term.strip() else None
            for item in lolesxi_data:
                if search_lower is None or search_lower in item.get("name", "").lower():
                    filtered.append(item)
        except Exception as e:
            logger.error("Error filtering LOLESXi: %s", e)
        return filtered
    
    def populate_tree(search_term=""):
        nonlocal full_data_store
        model.removeRows(0, model.rowCount())
        full_data_store.clear()
        
        try:
            filtered_data = filter_lolesxi(search_term)
            
            if not filtered_data:
                if not load_lolesxi_data():
                    QMessageBox.information(kb_window, "No LOLESXi Data", 
                        "No LOLESXi data found. Please ensure the data/linux/lolesxi directory exists and contains markdown files.")
                return
            
            for item in sorted(filtered_data, key=lambda x: x.get('name', '')):
                name = str(item.get('name', ''))
                tree_item = QStandardItem(name)
                model.appendRow(tree_item)
                full_data_store.append(item)
            
            logger.info("Displayed %s LOLESXi tools, stored %s items for detailed view", len(filtered_data), len(full_data_store))
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
                tool_name = item_data.get("name", "N/A")
                content = []
                content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
                name_padding = max(0, DETAIL_LINE_WIDTH - (len(tool_name) + 2))
                content.append(f"║  <b>{tool_name}</b>" + " " * name_padding + "║")
                content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
                content.append("")
                content.append("┌─ <b>Basic Information</b>")
                if item_data.get('description'):
                    content.append(f"│  Description: {item_data['description']}")
                if item_data.get('author'):
                    content.append(f"│  Author: {item_data['author']}")
                if item_data.get('created'):
                    content.append(f"│  Created: {item_data['created']}")
                if item_data.get('category'):
                    content.append(f"│  Category: {item_data['category']}")
                if item_data.get('mitre_id'):
                    content.append(f"│  MITRE ID: {item_data['mitre_id']}")
                if item_data.get('os'):
                    content.append(f"│  Operating System: {item_data['os']}")
                if item_data.get('privileges'):
                    content.append(f"│  Privileges: {item_data['privileges']}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                content.append("")
                if item_data.get('commands'):
                    content.append("┌─ <b>Commands</b>")
                    for i, cmd in enumerate(item_data['commands'], 1):
                        content.append(f"│")
                        content.append(f"│  [{i}] Command Details:")
                        content.append(f"│  ┌─ <span style='color: red; font-weight: bold;'>Command:</span> {cmd.get('Command', 'N/A')}")
                        
                        has_desc = bool(cmd.get('Description'))
                        has_usecase = bool(cmd.get('Usecase'))
                        has_category = bool(cmd.get('Category'))
                        has_privileges = bool(cmd.get('Privileges'))
                        has_mitre = bool(cmd.get('MitreID'))
                        has_os = bool(cmd.get('OperatingSystem'))
                        has_procedural = bool(cmd.get('ProceduralExamples'))
                        has_tags = bool(cmd.get('Tags'))
                        
                        has_any = has_desc or has_usecase or has_category or has_privileges or has_mitre or has_os or has_procedural or has_tags
                        
                        if has_desc:
                            connector = "├" if (has_usecase or has_category or has_privileges or has_mitre or has_os or has_procedural or has_tags) else "└"
                            content.append(f"│  {connector}─ Description: {cmd['Description']}")
                        
                        if has_usecase:
                            connector = "├" if (has_category or has_privileges or has_mitre or has_os or has_procedural or has_tags) else "└"
                            content.append(f"│  {connector}─ Usecase: {cmd['Usecase']}")
                        
                        if has_category:
                            connector = "├" if (has_privileges or has_mitre or has_os or has_procedural or has_tags) else "└"
                            content.append(f"│  {connector}─ Category: {cmd['Category']}")
                        
                        if has_privileges:
                            connector = "├" if (has_mitre or has_os or has_procedural or has_tags) else "└"
                            content.append(f"│  {connector}─ Privileges: {cmd['Privileges']}")
                        
                        if has_mitre:
                            connector = "├" if (has_os or has_procedural or has_tags) else "└"
                            content.append(f"│  {connector}─ MITRE ID: {cmd['MitreID']}")
                        
                        if has_os:
                            connector = "├" if (has_procedural or has_tags) else "└"
                            content.append(f"│  {connector}─ OS: {cmd['OperatingSystem']}")
                        
                        if has_procedural:
                            connector = "├" if has_tags else "└"
                            content.append(f"│  {connector}─ Procedural Examples:")
                            for example in cmd.get('ProceduralExamples', []):
                                content.append(f"│  │    • {example}")
                        
                        if has_tags:
                            tags = cmd.get('Tags', [])
                            tag_strings = []
                            if isinstance(tags, list):
                                for tag in tags:
                                    if isinstance(tag, dict):
                                        tag_strings.append(f"{list(tag.keys())[0]}: {list(tag.values())[0]}")
                                    else:
                                        tag_strings.append(str(tag))
                            else:
                                tag_strings.append(str(tags))
                            content.append(f"│  └─ Tags: {', '.join(tag_strings)}")
                        elif not has_any:
                            content.append(f"│  └")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if item_data.get('full_path'):
                    content.append("┌─ <b>Full Paths</b>")
                    for path_info in item_data['full_path']:
                        path = path_info.get('Path', path_info) if isinstance(path_info, dict) else path_info
                        content.append(f"│  • {path}")
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
                if item_data.get('atomic_tests'):
                    content.append("┌─ <b>Atomic Tests</b>")
                    for i, test in enumerate(item_data['atomic_tests'], 1):
                        if isinstance(test, dict):
                            link = test.get('Link', str(test))
                        else:
                            link = str(test)
                        content.append(f"│  {i}. {link}")
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
                if item_data.get('acknowledgement'):
                    content.append("┌─ <b>Acknowledgements</b>")
                    for ack in item_data['acknowledgement']:
                        if isinstance(ack, dict):
                            person = ack.get('Person', 'N/A')
                            handle = ack.get('Handle', 'N/A')
                            content.append(f"│  • Person: {person}")
                            if handle:
                                content.append(f"│    Handle: {handle}")
                        else:
                            content.append(f"│  • {ack}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                content.append("┌─ <b>Metadata</b>")
                content.append(f"│  File: {item_data.get('file', 'N/A')}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                html_content = "\n".join(content).replace("\n", "<br>")
                detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>{html_content}</pre>")
            else:
                detail_view.clear()
        except Exception as e:
            logger.error("Error in selection handler: %s", e)
            detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>Error loading tool details: {e}</pre>")
    
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

