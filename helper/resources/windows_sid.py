"""
Windows Security Identifier (SID) knowledge-base window for Kanvas: loads SID
data from YAML, provides search/filter and detail view. Cross-platform (Windows,
macOS, Linux): uses pathlib and explicit encoding; line endings normalized.
Revised on 01/02/2026 by Jinto Antony
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

SID_WINDOW = None
SID_DATA_CACHE = None
DETAIL_LINE_WIDTH = 78
DETAIL_BORDER_WIDTH = 77
DETAIL_CONTENT_WIDTH = 75


def format_sid_detail_content(sid, display_name, description):
    description = description or ""
    content = []
    content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
    sid_padding = max(0, DETAIL_LINE_WIDTH - (len(sid) + 2))
    content.append(f"║  <b>{sid}</b>" + " " * sid_padding + "║")
    content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
    content.append("")
    content.append("┌─ <b>Display Name</b>")
    content.append(f"│  {display_name}")
    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
    content.append("")
    content.append("┌─ <b>Description</b>")
    for line in description.splitlines():
        current_line = ""
        for word in line.split():
            if len(current_line) + len(word) + 1 <= DETAIL_CONTENT_WIDTH:
                current_line = f"{current_line} {word}".strip() if current_line else word
            else:
                if current_line:
                    content.append(f"│  {current_line}")
                current_line = word
        if current_line:
            content.append(f"│  {current_line}")
    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
    return "\n".join(content).replace("\n", "<br>")


def load_sid_data():
    global SID_DATA_CACHE
    if SID_DATA_CACHE is not None:
        return SID_DATA_CACHE
    base_dir = Path(__file__).parent.parent.parent
    sid_file = base_dir / "data" / "microsoft" / "sid.yml"
    sid_file_path = sid_file
    if not sid_file_path.exists():
        microsoft_dir = base_dir / "data" / "microsoft"
        if microsoft_dir.exists():
            for f in microsoft_dir.iterdir():
                if f.name.lower() in ("sid.yml", "sid.yaml"):
                    sid_file_path = f
                    break
    try:
        if not sid_file_path.exists():
            logger.error("SID file not found: %s", sid_file)
            return []
        with open(sid_file_path, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
        if data and "sids" in data:
            sid_data = data["sids"]
            logger.info("Loaded %s SIDs from %s", len(sid_data), sid_file_path)
        else:
            logger.warning("No SIDs found in YAML file.")
            return []
    except yaml.YAMLError as e:
        logger.error("YAML parse error in %s: %s", sid_file_path, e)
        return []
    except Exception as e:
        logger.error("Error loading SID data: %s", e)
        return []
    SID_DATA_CACHE = sid_data
    return sid_data


def show_detailed_view(parent, sid_data):
    detail_dialog = QDialog(parent)
    sid = sid_data.get("sid", "Unknown")
    display_name = sid_data.get("display_name", "Unknown")
    detail_dialog.setWindowTitle(f"SID Details - {sid}")
    detail_dialog.resize(900, 700)
    detail_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

    layout = QVBoxLayout(detail_dialog)
    title_label = QLabel(f"SID Details - {sid}")
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
    sid_val = sid_data.get("sid", "N/A")
    display_name_val = sid_data.get("display_name", "N/A")
    description = sid_data.get("description", "N/A")
    html_content = format_sid_detail_content(sid_val, display_name_val, description)
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


def display_windows_sid_kb(parent, db_path):
    global SID_WINDOW
    if SID_WINDOW is not None:
        SID_WINDOW.activateWindow()
        SID_WINDOW.raise_()
        return SID_WINDOW
    data = load_sid_data()
    if not data:
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
    kb_window = QWidget(parent.window)
    kb_window.setWindowTitle("Windows Security Identifiers (SIDs)")
    kb_window.resize(1200, 800)
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    SID_WINDOW = kb_window

    original_close_event = kb_window.closeEvent
    def custom_close_event(event):
        global SID_WINDOW
        SID_WINDOW = None
        if original_close_event:
            original_close_event(event)
    kb_window.closeEvent = custom_close_event

    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    header_layout = QHBoxLayout()
    title_label = QLabel("Windows Security Identifiers (SIDs)")
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
    search_textbox.setPlaceholderText("Search SIDs (SID, display name, description...)")
    search_textbox.setFixedWidth(400)
    filter_layout.addWidget(search_textbox)
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
    model.setHorizontalHeaderLabels(["SID", "Display Name"])
    tree_view.setModel(model)
    tree_view.setColumnWidth(0, 250)
    tree_view.setColumnWidth(1, 300)
    splitter.addWidget(tree_view)
    detail_view = QTextEdit()
    detail_view.setReadOnly(True)
    detail_view.setFont(QFont("Consolas", 10) or QFont("Courier New", 10))
    detail_view.setStyleSheet(styles.DETAIL_VIEW_KB_STYLE)
    detail_view.setPlaceholderText("Select a SID to view details...")
    splitter.addWidget(detail_view)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    main_layout.addWidget(splitter, 1)

    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: Microsoft Windows Security Identifiers")
    footer_layout.addWidget(footer_label)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)

    full_data_store = []

    def filter_sids(search_text=""):
        filtered = []
        try:
            sid_data = load_sid_data()
            if not sid_data:
                return []
            search_lower = search_text.lower() if search_text else None
            for sid_entry in sid_data:
                if search_lower is not None:
                    sid_match = search_lower in sid_entry.get("sid", "").lower()
                    name_match = search_lower in sid_entry.get("display_name", "").lower()
                    desc_match = search_lower in sid_entry.get("description", "").lower()
                    if not (sid_match or name_match or desc_match):
                        continue
                filtered.append(sid_entry)
        except Exception as e:
            logger.error("Error filtering SIDs: %s", e)
        return filtered

    def populate_tree(search_text=""):
        nonlocal full_data_store
        model.removeRows(0, model.rowCount())
        full_data_store.clear()
        try:
            filtered_data = filter_sids(search_text)
            if not filtered_data:
                if not load_sid_data():
                    QMessageBox.information(kb_window, "No SID Data", "No SID data found. Please ensure the data/microsoft/sid.yml file exists.")
                return
            for sid_entry in sorted(filtered_data, key=lambda x: x.get("sid", "")):
                sid = sid_entry.get("sid", "N/A")
                display_name = sid_entry.get("display_name", "N/A")
                sid_item = QStandardItem(sid)
                name_item = QStandardItem(display_name)
                model.appendRow([sid_item, name_item])
                full_data_store.append(sid_entry)
            logger.info("Displayed %s SIDs, stored %s items for detailed view", len(filtered_data), len(full_data_store))
        except Exception as e:
            logger.error("Error populating tree: %s", e)
            QMessageBox.critical(kb_window, "Error", f"Failed to populate data: {e}")

    def update_display():
        populate_tree(search_textbox.text())

    def on_item_selected(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                sid_data = full_data_store[row]
                sid = sid_data.get("sid", "N/A")
                display_name = sid_data.get("display_name", "N/A")
                description = sid_data.get("description", "N/A")
                html_content = format_sid_detail_content(sid, display_name, description)
                detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>{html_content}</pre>")
            else:
                detail_view.clear()
        except Exception as e:
            logger.error("Error in selection handler: %s", e)
            detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>Error loading SID details: {e}</pre>")

    def on_item_double_clicked(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                show_detailed_view(kb_window, full_data_store[row])
        except Exception as e:
            logger.error("Error in double-click handler: %s", e)
            QMessageBox.warning(kb_window, "Error", f"Failed to open detailed view: {e}")

    tree_view.selectionModel().currentChanged.connect(on_item_selected)
    tree_view.doubleClicked.connect(on_item_double_clicked)
    search_textbox.textChanged.connect(update_display)
    populate_tree()

    kb_window.show()
    return kb_window
