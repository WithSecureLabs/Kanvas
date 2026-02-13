"""
Forensic Artifacts knowledge-base window for Kanvas: loads artifact definitions
from data/artifacts YAML files, provides search, OS/category filters, and detail
view. Cross-platform (Windows, macOS, Linux). Revised on 01/02/2026 by Jinto Antony
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

ARTIFACTS_WINDOW = None
ARTIFACTS_DATA_CACHE = None
DETAIL_LINE_WIDTH = 78
DETAIL_BORDER_WIDTH = 77


def load_artifacts_data():
    global ARTIFACTS_DATA_CACHE
    if ARTIFACTS_DATA_CACHE is not None:
        return ARTIFACTS_DATA_CACHE
    artifacts_data = []
    base_dir = Path(__file__).parent.parent.parent
    artifacts_dir = base_dir / "data" / "artifacts"
    try:
        if not artifacts_dir.exists():
            logger.error("Artifacts directory not found: %s", artifacts_dir)
            return []
        yaml_files = [f for f in artifacts_dir.iterdir() if f.is_file() and f.suffix.lower() in (".yaml", ".yml")]
        logger.info("Found %s YAML files in artifacts directory", len(yaml_files))
        if not yaml_files:
            logger.warning("No YAML files found in artifacts directory.")
            return []
        for yaml_path in yaml_files:
            try:
                with open(yaml_path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                documents = content.split("---")
                for doc in documents:
                    doc = doc.strip()
                    if not doc or doc.startswith("#"):
                        continue
                    try:
                        artifact = yaml.safe_load(doc)
                        if artifact and ("name" in artifact or "Name" in artifact):
                            if "Name" in artifact and "name" not in artifact:
                                artifact["name"] = artifact.pop("Name")
                            artifact["category"] = yaml_path.stem
                            artifact["file"] = yaml_path.name
                            artifacts_data.append(artifact)
                    except yaml.YAMLError as e:
                        logger.error("YAML parse error in %s: %s", yaml_path, e)
                        continue
            except Exception as e:
                logger.error("Error loading %s: %s", yaml_path, e)
                continue
        logger.info("Loaded %s artifacts from %s files", len(artifacts_data), len(yaml_files))
    except Exception as e:
        logger.error("Error loading artifacts data: %s", e)
    
    ARTIFACTS_DATA_CACHE = artifacts_data
    return artifacts_data


NO_DATA_MSG = "No data found. Please click 'Download Updates' to download the latest files."


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

def show_detailed_view(parent, artifact_data):
    detail_dialog = QDialog(parent)
    detail_dialog.setWindowTitle(f"Artifact Details - {artifact_data.get('name', 'Unknown')}")
    detail_dialog.resize(900, 700)
    detail_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    layout = QVBoxLayout(detail_dialog)
    
    title_label = QLabel(f"Artifact Details - {artifact_data.get('name', 'Unknown Artifact')}")
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
    artifact_name = artifact_data.get("name", artifact_data.get("Name", "Unknown"))
    content = []
    content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
    name_padding = max(0, DETAIL_LINE_WIDTH - (len(artifact_name) + 2))
    content.append(f"║  <b>{artifact_name}</b>" + " " * name_padding + "║")
    content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
    content.append("")
    content.append("┌─ <b>General Information</b>")
    if artifact_data.get('aliases'):
        content.append(f"│  Aliases: {', '.join(artifact_data['aliases'])}")
    if artifact_data.get('supported_os'):
        content.append(f"│  Supported OS: {', '.join(artifact_data['supported_os'])}")
    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
    content.append("")
    if artifact_data.get("doc"):
        content.append("┌─ <b>Description</b>")
        doc = artifact_data["doc"].strip()
        for line in doc.splitlines():
            content.append(f"│  {line}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if artifact_data.get('sources'):
        content.append("┌─ <b>Sources</b>")
        for i, source in enumerate(artifact_data['sources'], 1):
            content.append(f"│")
            content.append(f"│  [{i}] Source Details:")
            content.append(f"│  ┌─ Type: {source.get('type', 'N/A')}")
            
            attrs = source.get('attributes', {})
            has_supported_os = bool(source.get('supported_os'))
            has_paths = bool(attrs.get('paths'))
            has_cmd = bool(attrs.get('cmd'))
            has_keys = bool(attrs.get('keys'))
            has_key_value_pairs = bool(attrs.get('key_value_pairs'))
            
            has_any_attrs = has_paths or has_cmd or has_keys or has_key_value_pairs
            
            if has_supported_os:
                connector = "├" if has_any_attrs else "└"
                content.append(f"│  {connector}─ OS: {', '.join(source['supported_os'])}")
            
            if has_paths:
                connector = "├" if (has_cmd or has_keys or has_key_value_pairs) else "└"
                content.append(f"│  {connector}─ Paths:")
                for path in attrs['paths']:
                    content.append(f"│  │    • {path}")
            
            if has_cmd:
                connector = "├" if (has_keys or has_key_value_pairs) else "└"
                content.append(f"│  {connector}─ Command: {attrs['cmd']}")
                if attrs.get('args'):
                    content.append(f"│  │    Arguments: {' '.join(attrs['args'])}")
            
            if has_keys:
                connector = "├" if has_key_value_pairs else "└"
                content.append(f"│  {connector}─ Registry Keys:")
                for key in attrs['keys']:
                    content.append(f"│  │    • {key}")
            
            if has_key_value_pairs:
                content.append(f"│  └─ Registry Values:")
                for kv in attrs['key_value_pairs']:
                    content.append(f"│       • {kv.get('key')}: {kv.get('value')}")
            elif not has_any_attrs and not has_supported_os:
                content.append(f"│  └")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    if artifact_data.get('urls'):
        content.append("┌─ <b>References</b>")
        for url in artifact_data['urls']:
            content.append(f"│  • {url}")
        content.append("└" + "─" * DETAIL_BORDER_WIDTH)
        content.append("")
    content.append("┌─ <b>Metadata</b>")
    content.append(f"│  Category: {artifact_data.get('category', 'N/A')}")
    content.append(f"│  File: {artifact_data.get('file', 'N/A')}")
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

def display_artifacts_kb(parent, db_path):
    global ARTIFACTS_WINDOW
    if ARTIFACTS_WINDOW is not None:
        ARTIFACTS_WINDOW.activateWindow()
        ARTIFACTS_WINDOW.raise_()
        return ARTIFACTS_WINDOW
    data = load_artifacts_data()
    if not data:
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
    kb_window = QWidget(parent.window)
    kb_window.setWindowTitle("Forensic Artifacts - Common Locations on Disk")
    kb_window.resize(1200, 800)
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    ARTIFACTS_WINDOW = kb_window
    
    original_close_event = kb_window.closeEvent
    def custom_close_event(event):
        global ARTIFACTS_WINDOW
        ARTIFACTS_WINDOW = None
        if original_close_event:
            original_close_event(event)
    kb_window.closeEvent = custom_close_event
    
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    header_layout = QHBoxLayout()
    title_label = QLabel("Forensic Artifacts - Common Locations on Disk")
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
    search_textbox.setPlaceholderText("Search artifacts (name, description, paths...)")
    search_textbox.setFixedWidth(300)
    filter_layout.addWidget(search_textbox)
    
    filter_layout.addSpacing(10)
    
    os_label = QLabel("OS:")
    os_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(os_label)
    
    os_filter = QComboBox()
    os_filter.addItems(["All", "Windows", "Linux", "Darwin"])
    os_filter.setFixedWidth(150)
    filter_layout.addWidget(os_filter)
    
    filter_layout.addSpacing(10)
    
    category_label = QLabel("Category:")
    category_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(category_label)
    
    category_filter = QComboBox()
    category_filter.addItem("All")
    category_filter.setFixedWidth(200)
    filter_layout.addWidget(category_filter)
    
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
    detail_view.setPlaceholderText("Select an artifact to view details...")
    splitter.addWidget(detail_view)
    
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 1)
    
    main_layout.addWidget(splitter, 1)
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://github.com/ForensicArtifacts/artifacts-kb'>https://github.com/ForensicArtifacts/artifacts-kb</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)
    
    full_data_store = []
    
    def filter_artifacts(search_text="", os_filter_text="All", category_filter_text="All"):
        filtered = []
        try:
            artifacts_data = load_artifacts_data()
            if not artifacts_data:
                return []
            
            search_lower = search_text.strip().lower() if search_text else None
            for artifact in artifacts_data:
                if search_lower is not None:
                    artifact_name = artifact.get("name", artifact.get("Name", ""))
                    name_match = search_lower in str(artifact_name).lower()
                    doc_match = search_lower in artifact.get("doc", "").lower()
                    sources_match = False
                    for source in artifact.get("sources", []):
                        attrs = source.get("attributes", {})
                        for path in attrs.get("paths", []):
                            if search_lower in str(path).lower():
                                sources_match = True
                                break
                        if sources_match:
                            break
                    if not (name_match or doc_match or sources_match):
                        continue
                if os_filter_text != "All":
                    supported_os = artifact.get('supported_os', [])
                    if os_filter_text not in supported_os:
                        continue
                if category_filter_text != "All":
                    if artifact.get('category') != category_filter_text:
                        continue
                
                filtered.append(artifact)
        except Exception as e:
            logger.error("Error filtering artifacts: %s", e)
        return filtered
    
    def populate_tree(search_text="", os_filter_text="All", category_filter_text="All"):
        nonlocal full_data_store
        model.removeRows(0, model.rowCount())
        full_data_store.clear()
        
        try:
            filtered_data = filter_artifacts(search_text, os_filter_text, category_filter_text)
            
            if not filtered_data:
                if not load_artifacts_data():
                    QMessageBox.information(kb_window, "No Artifacts Data", 
                        "No artifacts data found. Please ensure the data/artifacts directory exists and contains YAML files.")
                    return
            for artifact in sorted(filtered_data, key=lambda x: x.get('name', x.get('Name', ''))):
                name = str(artifact.get('name', artifact.get('Name', '')))
                
                item = QStandardItem(name)
                model.appendRow(item)
                full_data_store.append(artifact)
            
            logger.info("Displayed %s artifacts, stored %s items for detailed view", len(filtered_data), len(full_data_store))
        except Exception as e:
            logger.error("Error populating tree: %s", e)
            QMessageBox.critical(kb_window, "Error", f"Failed to populate data: {e}")
    
    def update_display():
        search_text = search_textbox.text()
        os_filter_text = os_filter.currentText()
        category_filter_text = category_filter.currentText()
        populate_tree(search_text, os_filter_text, category_filter_text)
    
    def on_item_selected(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                artifact_data = full_data_store[row]
                artifact_name = artifact_data.get("name", artifact_data.get("Name", "N/A"))
                content = []
                content.append("╔" + "═" * DETAIL_LINE_WIDTH + "╗")
                name_padding = max(0, DETAIL_LINE_WIDTH - (len(artifact_name) + 2))
                content.append(f"║  <b>{artifact_name}</b>" + " " * name_padding + "║")
                content.append("╚" + "═" * DETAIL_LINE_WIDTH + "╝")
                content.append("")
                content.append("┌─ <b>General Information</b>")
                if artifact_data.get('aliases'):
                    content.append(f"│  Aliases: {', '.join(artifact_data['aliases'])}")
                if artifact_data.get('supported_os'):
                    content.append(f"│  Supported OS: {', '.join(artifact_data['supported_os'])}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                content.append("")
                if artifact_data.get("doc"):
                    content.append("┌─ <b>Description</b>")
                    doc = artifact_data["doc"].strip()
                    for line in doc.splitlines():
                        content.append(f"│  {line}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                if artifact_data.get('sources'):
                    content.append("┌─ <b>Sources</b>")
                    for i, source in enumerate(artifact_data['sources'], 1):
                        content.append(f"│")
                        content.append(f"│  [{i}] Source Details:")
                        content.append(f"│  ┌─ Type: {source.get('type', 'N/A')}")
                        
                        attrs = source.get('attributes', {})
                        has_supported_os = bool(source.get('supported_os'))
                        has_paths = bool(attrs.get('paths'))
                        has_cmd = bool(attrs.get('cmd'))
                        has_keys = bool(attrs.get('keys'))
                        has_key_value_pairs = bool(attrs.get('key_value_pairs'))
                        
                        has_any_attrs = has_paths or has_cmd or has_keys or has_key_value_pairs
                        
                        if has_supported_os:
                            connector = "├" if has_any_attrs else "└"
                            content.append(f"│  {connector}─ OS: {', '.join(source['supported_os'])}")
                        
                        if has_paths:
                            connector = "├" if (has_cmd or has_keys or has_key_value_pairs) else "└"
                            content.append(f"│  {connector}─ Paths:")
                            for path in attrs['paths']:
                                content.append(f"│  │    • {path}")
                        
                        if has_cmd:
                            connector = "├" if (has_keys or has_key_value_pairs) else "└"
                            content.append(f"│  {connector}─ Command: {attrs['cmd']}")
                            if attrs.get('args'):
                                content.append(f"│  │    Arguments: {' '.join(attrs['args'])}")
                        
                        if has_keys:
                            connector = "├" if has_key_value_pairs else "└"
                            content.append(f"│  {connector}─ Registry Keys:")
                            for key in attrs['keys']:
                                content.append(f"│  │    • {key}")
                        
                        if has_key_value_pairs:
                            content.append(f"│  └─ Registry Values:")
                            for kv in attrs['key_value_pairs']:
                                content.append(f"│       • {kv.get('key')}: {kv.get('value')}")
                        elif not has_any_attrs and not has_supported_os:
                            content.append(f"│  └")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                
                if artifact_data.get('urls'):
                    content.append("┌─ <b>References</b>")
                    for url in artifact_data['urls']:
                        content.append(f"│  • {url}")
                    content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                    content.append("")
                
                content.append("┌─ <b>Metadata</b>")
                content.append(f"│  Category: {artifact_data.get('category', 'N/A')}")
                content.append(f"│  File: {artifact_data.get('file', 'N/A')}")
                content.append("└" + "─" * DETAIL_BORDER_WIDTH)
                html_content = "\n".join(content).replace("\n", "<br>")
                detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>{html_content}</pre>")
            else:
                detail_view.clear()
        except Exception as e:
            logger.error("Error in selection handler: %s", e)
            detail_view.setHtml(f"<pre style='font-family: {styles.FONT_KB_MONOSPACE};'>Error loading artifact details: {e}</pre>")
    
    def on_item_double_clicked(index):
        try:
            row = index.row()
            if 0 <= row < len(full_data_store):
                artifact_data = full_data_store[row]
                show_detailed_view(kb_window, artifact_data)
        except Exception as e:
            logger.error("Error in double-click handler: %s", e)
            QMessageBox.warning(kb_window, "Error", f"Failed to open detailed view: {e}")
    
    tree_view.selectionModel().currentChanged.connect(on_item_selected)
    tree_view.doubleClicked.connect(on_item_double_clicked)
    search_textbox.textChanged.connect(update_display)
    os_filter.currentTextChanged.connect(update_display)
    category_filter.currentTextChanged.connect(update_display)
    try:
        artifacts_data = load_artifacts_data()
        if artifacts_data:
            categories = sorted(set(a.get('category', 'Unknown') for a in artifacts_data))
            category_filter.addItems(categories)
    except Exception as e:
        logger.error("Error populating category filter: %s", e)
    populate_tree()
    
    kb_window.show()
    return kb_window

