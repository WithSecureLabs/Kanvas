# code reviewed 
import os
import yaml
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeView, QPushButton, 
    QSizePolicy, QMessageBox, QLineEdit, QTextEdit, QDialog
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

LOLBAS_WINDOW = None
LOLBAS_DATA_CACHE = None

def load_lolbas_data():
    global LOLBAS_DATA_CACHE
    if LOLBAS_DATA_CACHE is not None:
        return LOLBAS_DATA_CACHE
    lolbas_data = []
    lolbas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lolbas")
    try:
        if not os.path.exists(lolbas_dir):
            logger.error(f"LOLBAS directory not found: {lolbas_dir}")
            logger.warning("LOLBAS directory does not exist. Please click 'Download Updates' to download LOLBAS data.")
            return []
        yml_files = [f for f in os.listdir(lolbas_dir) if f.endswith('.yml')]
        logger.info(f"Found {len(yml_files)} YAML files in LOLBAS directory")
        if not yml_files:
            logger.warning("No YAML files found in LOLBAS directory. Please click 'Download Updates' to download LOLBAS data.")
            return []
        for yml_file in yml_files:
            yml_path = os.path.join(lolbas_dir, yml_file)
            try:
                with open(yml_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    if data and 'Name' in data:
                        commands = data.get('Commands', [])
                        first_command = commands[0] if commands else {}
                        lolbas_data.append({
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
                            'resources': data.get('Resources', []),
                            'acknowledgement': data.get('Acknowledgement', []),
                            'file': yml_file
                        })
            except Exception as e:
                logger.error(f"Error loading {yml_file}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error loading LOLBAS data: {e}")
    LOLBAS_DATA_CACHE = lolbas_data
    return lolbas_data

def show_detailed_view(parent, item_data):
    detail_dialog = QDialog(parent)
    detail_dialog.setWindowTitle(f"LOLBAS Details - {item_data.get('name', 'Unknown')}")
    detail_dialog.resize(900, 700)
    detail_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    layout = QVBoxLayout(detail_dialog)
    title_label = QLabel(f"LOLBAS Details - {item_data.get('name', 'Unknown Tool')}")
    title_font = QFont()
    title_font.setPointSize(14)
    title_font.setBold(True)
    title_label.setFont(title_font)
    title_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_label)
    text_area = QTextEdit()
    text_area.setReadOnly(True)
    text_area.setFont(QFont("Courier New", 10))
    text_area.setStyleSheet("""
        QTextEdit {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }
    """)
    content = []
    content.append("=" * 80)
    content.append(f"LOLBAS DETAILS: {item_data.get('name', 'Unknown')}")
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
            content.append(f"  Command: {cmd.get('Command', 'N/A')}")
            content.append(f"  Description: {cmd.get('Description', 'N/A')}")
            content.append(f"  Usecase: {cmd.get('Usecase', 'N/A')}")
            content.append(f"  Category: {cmd.get('Category', 'N/A')}")
            content.append(f"  Privileges: {cmd.get('Privileges', 'N/A')}")
            content.append(f"  MITRE ID: {cmd.get('MitreID', 'N/A')}")
            content.append(f"  OS: {cmd.get('OperatingSystem', 'N/A')}")
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
            content.append(f"  {path_info.get('Path', 'N/A')}")
        content.append("")
    if item_data.get('code_sample'):
        content.append("CODE SAMPLES:")
        content.append("-" * 40)
        for code in item_data.get('code_sample', []):
            if isinstance(code, dict):
                content.append(f"  {code.get('Code', 'N/A')}")
            else:
                content.append(f"  {code}")
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
                content.append(f"  Handle: {handle}")
            else:
                content.append(f"  {ack}")
        content.append("")
    content.append("=" * 80)
    text_area.setPlainText("\n".join(content))
    layout.addWidget(text_area)
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet("background-color: #4CAF50; color: white;")
    close_button.clicked.connect(detail_dialog.close)
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    layout.addLayout(button_layout)
    detail_dialog.exec()

def display_lolbas_kb(parent, db_path):
    global LOLBAS_WINDOW
    if LOLBAS_WINDOW is not None:
        LOLBAS_WINDOW.activateWindow()
        LOLBAS_WINDOW.raise_()
        return
    kb_window = QWidget(parent.window)
    kb_window.setWindowTitle("LOLBAS - Living Off The Land Binaries")
    kb_window.resize(1000, 800)
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    LOLBAS_WINDOW = kb_window
    original_close_event = kb_window.closeEvent
    def custom_close_event(event):
        global LOLBAS_WINDOW
        LOLBAS_WINDOW = None
        if original_close_event:
            original_close_event(event)
    kb_window.closeEvent = custom_close_event
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
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
    tree_view = QTreeView()
    tree_view.setRootIsDecorated(False)
    tree_view.setAlternatingRowColors(True)
    tree_view.setSelectionBehavior(QTreeView.SelectRows)
    tree_view.setSortingEnabled(True)
    tree_view.setStyleSheet("""
        QTreeView {
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            selection-background-color: #007acc;
            selection-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            gridline-color: #e9ecef;
            font-size: 10pt;
        }
        QTreeView::item {
            padding: 6px 10px;
            border-bottom: 1px solid #f1f3f4;
        }
        QTreeView::item:hover {
            background-color: #e3f2fd;
        }
        QTreeView::item:selected {
            background-color: #007acc;
            color: white;
        }
        QHeaderView::section {
            background-color: #f8f9fa;
            color: #495057;
            padding: 10px 12px;
            border: none;
            border-bottom: 2px solid #dee2e6;
            border-right: 1px solid #e9ecef;
            font-weight: bold;
            font-size: 10pt;
        }
        QHeaderView::section:hover {
            background-color: #e9ecef;
        }
    """)
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Name", "Description", "Category", "MITRE ID", "OS"])
    tree_view.setModel(model)
    tree_view.setColumnWidth(0, 200)
    tree_view.setColumnWidth(1, 400)
    tree_view.setColumnWidth(2, 150)
    tree_view.setColumnWidth(3, 120)
    tree_view.setColumnWidth(4, 150)
    main_layout.addWidget(tree_view, 1)
    full_data_store = []
    
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://lolbas-project.github.io'>lolbas-project.github.io</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)
    def populate_tree(search_term=""):
        nonlocal full_data_store
        model.removeRows(0, model.rowCount())
        full_data_store.clear()
        try:
            lolbas_data = load_lolbas_data()
            if not lolbas_data:
                QMessageBox.information(kb_window, "No LOLBAS Data", 
                    "No LOLBAS data found. Please click 'Download Updates' to download the latest LOLBAS information.")
                return
            filtered_data = []
            for item in lolbas_data:
                name_match = not search_term.strip() or search_term.lower() in item['name'].lower()
                if name_match:
                    filtered_data.append(item)
                    full_data_store.append(item)
            for item in filtered_data:
                name = str(item.get('name', ''))
                description = str(item.get('description', ''))
                if len(description) > 80:
                    description = description[:80] + "..."
                category = str(item.get('category', ''))
                mitre_id = str(item.get('mitre_id', ''))
                os_info = str(item.get('os', ''))
                if len(os_info) > 50:
                    os_info = os_info[:50] + "..."
                items = [
                    QStandardItem(name),
                    QStandardItem(description),
                    QStandardItem(category),
                    QStandardItem(mitre_id),
                    QStandardItem(os_info)
                ]
                model.appendRow(items)
            logger.info(f"Displayed {len(filtered_data)} LOLBAS tools, stored {len(full_data_store)} items for detailed view")
        except Exception as e:
            logger.error(f"Error populating tree: {e}")
            QMessageBox.critical(kb_window, "Error", f"Failed to populate data: {e}")
    def search_tools():
        search_term = search_textbox.text()
        populate_tree(search_term)
    def on_item_double_clicked(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                item_data = full_data_store[row]
                show_detailed_view(kb_window, item_data)
            else:
                logger.warning(f"Invalid row index: {row}, data store length: {len(full_data_store)}")
        except Exception as e:
            logger.error(f"Error in double-click handler: {e}")
            QMessageBox.warning(kb_window, "Error", f"Failed to open detailed view: {e}")
    tree_view.doubleClicked.connect(on_item_double_clicked)
    search_textbox.textChanged.connect(search_tools)
    populate_tree("")
    kb_window.show()
    return kb_window