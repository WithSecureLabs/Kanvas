# code reviewed 
import sqlite3
import logging
import webbrowser
from collections import defaultdict
from contextlib import contextmanager
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QMessageBox, QSizePolicy, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QComboBox, QTreeView
)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

def display_msportals_data(parent, db_path):
    if hasattr(parent, 'msportals_window') and parent.msportals_window is not None:
        if parent.msportals_window.isVisible():
            parent.msportals_window.raise_()
            parent.msportals_window.activateWindow()
            return parent.msportals_window
        else:
            parent.msportals_window = None
    
    parent.msportals_window = QWidget(parent.window)
    parent.msportals_window.setWindowTitle("Microsoft Azure / Entra Portals")
    parent.msportals_window.resize(1000, 800)
    parent.msportals_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    main_layout = QVBoxLayout(parent.msportals_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    
    header_layout = QHBoxLayout()
    title_label = QLabel("Microsoft Azure / Entra Portals")
    title_font = QFont()
    title_font.setBold(True)
    title_font.setPointSize(16)
    title_label.setFont(title_font)
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    
    search_layout = QHBoxLayout()
    search_label = QLabel("Search:")
    search_input = QLineEdit()
    search_input.setPlaceholderText("Search portals...")
    search_layout.addWidget(search_label)
    search_layout.addWidget(search_input)
    search_layout.addStretch()
    
    main_layout.addLayout(header_layout)
    main_layout.addLayout(search_layout)
    
    tree_widget = QTreeWidget()
    tree_widget.setHeaderLabels(["Portal Name", "URL"])
    tree_widget.setAlternatingRowColors(True)
    tree_widget.setRootIsDecorated(True)
    tree_widget.setSortingEnabled(True)
    tree_widget.setColumnWidth(0, 300)
    tree_widget.setColumnWidth(1, 600)
    tree_widget.header().setStretchLastSection(True)
    tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    tree_widget.header().setSectionResizeMode(1, QHeaderView.Stretch)
    
    populate_msportals_data(tree_widget, db_path)
    tree_widget.resizeColumnToContents(0)
    tree_widget.resizeColumnToContents(1)
    
    scroll_area = QScrollArea()
    scroll_area.setWidget(tree_widget)
    scroll_area.setWidgetResizable(True)
    main_layout.addWidget(scroll_area)
    
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://msportals.io'>msportals.io</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    
    main_layout.addLayout(footer_layout)
    
    search_input.textChanged.connect(lambda text: filter_tree(tree_widget, text))
    tree_widget.itemDoubleClicked.connect(lambda item, column: open_url(item, column))
    
    def close_event(event):
        parent.msportals_window = None
        event.accept()
    
    parent.msportals_window.closeEvent = close_event
    parent.msportals_window.show()
    return parent.msportals_window

def populate_msportals_data(tree_widget, db_path):
    try:
        with db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT group_name, portal_name, primary_url 
                FROM bookmarks 
                WHERE group_name LIKE '%Microsoft%' OR group_name LIKE '%Azure%' 
                ORDER BY group_name, portal_name
            """)
            rows = cursor.fetchall()
            
            categories = defaultdict(list)
            for group_name, portal_name, url in rows:
                category = categorize_portal(group_name, portal_name)
                categories[category].append((portal_name, url))
            
            for category, portals in categories.items():
                category_item = QTreeWidgetItem(tree_widget)
                category_item.setText(0, category)
                category_item.setFont(0, QFont("Arial", 10, QFont.Bold))
                
                for portal_name, url in portals:
                    portal_item = QTreeWidgetItem(category_item)
                    portal_item.setText(0, portal_name)
                    portal_item.setText(1, url)
                    portal_item.setToolTip(1, f"Click to open: {url}")
                
                category_item.setExpanded(True)
                
    except sqlite3.Error as e:
        logger.error(f"Failed to populate msportals data: {e}")

def categorize_portal(group_name, portal_name):
    name_lower = portal_name.lower()
    group_lower = group_name.lower()
    
    if any(gov in group_lower for gov in ['us gov', 'gcc', 'dod', 'china']):
        return 'Government Clouds'
    elif any(ai in name_lower for ai in ['ai', 'copilot', 'intelligence', 'cortana']):
        return 'AI & Intelligence'
    elif any(sec in name_lower for sec in ['security', 'defender', 'compliance']):
        return 'Security & Compliance'
    elif 'azure' in name_lower or 'azure' in group_lower:
        return 'Azure Services'
    elif any(m365 in name_lower for m365 in ['365', 'office', 'teams', 'sharepoint', 'exchange', 'outlook', 'word', 'excel', 'powerpoint']):
        return 'Microsoft 365'
    elif any(dev in name_lower for dev in ['dev', 'developer', 'studio', 'visual', 'code']):
        return 'Development Tools'
    elif 'admin' in name_lower or 'admin' in group_lower:
        return 'Admin Centers'
    elif any(lic in name_lower for lic in ['licensing', 'pricing', 'subscription']):
        return 'Licensing & Pricing'
    elif any(partner in group_lower for partner in ['partner', 'trial', 'msp']):
        return 'Partner & Trials'
    elif 'non-microsoft' in group_lower or '3rd party' in group_lower:
        return 'Third-Party Tools'
    elif 'end user' in group_lower:
        return 'End User Portals'
    else:
        return 'Other'

def filter_tree(tree_widget, search_text):
    for i in range(tree_widget.topLevelItemCount()):
        category_item = tree_widget.topLevelItem(i)
        category_visible = False
        
        for j in range(category_item.childCount()):
            portal_item = category_item.child(j)
            portal_name = portal_item.text(0).lower()
            url = portal_item.text(1).lower()
            
            if search_text.lower() in portal_name or search_text.lower() in url:
                portal_item.setHidden(False)
                category_visible = True
            else:
                portal_item.setHidden(True)
        
        category_item.setHidden(not category_visible)

def open_url(item, column):
    if column == 1:
        url = item.text(1)
        if url:
            webbrowser.open(url)

def display_event_id_kb(parent, db_path):
    if hasattr(parent, 'eventid_window') and parent.eventid_window is not None:
        if parent.eventid_window.isVisible():
            parent.eventid_window.raise_()
            parent.eventid_window.activateWindow()
            return parent.eventid_window
        else:
            parent.eventid_window = None
    
    parent.eventid_window = QWidget(parent.window)
    parent.eventid_window.setWindowTitle("Windows Event ID Lookup")
    parent.eventid_window.resize(1000, 800)
    parent.eventid_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    main_layout = QVBoxLayout(parent.eventid_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    
    header_layout = QHBoxLayout()
    title_label = QLabel("Windows Event ID Lookup")
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
    
    category_label = QLabel("Category:")
    category_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(category_label)
    
    categories = ["All"]
    try:
        with db_connection(db_path, parent.eventid_window) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evtx_id'")
            if not cursor.fetchone():
                QMessageBox.warning(parent.eventid_window, "Missing Data", "The Event ID database table (evtx_id) does not exist. Please run the update function to create it.")
            else:
                cursor.execute("SELECT DISTINCT category FROM evtx_id")
                db_categories = [row[0] for row in cursor.fetchall() if row[0]]
                categories.extend(sorted(db_categories))
                logger.info(f"Found {len(db_categories)} categories: {db_categories}")
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        QMessageBox.critical(parent.eventid_window, "Error", f"Failed to fetch categories: {e}")
    
    category_dropdown = QComboBox()
    category_dropdown.addItems(categories)
    category_dropdown.setFixedWidth(250)
    filter_layout.addWidget(category_dropdown)
    
    search_label = QLabel("Search Event ID:")
    search_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(search_label)
    
    search_textbox = QLineEdit()
    search_textbox.setPlaceholderText("Enter Event ID to search...")
    search_textbox.setFixedWidth(200)
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
            alternate-background-color: #fafbfc;
            selection-background-color: #0078d4;
            selection-color: white;
            border: 1px solid #d1d5da;
            border-radius: 6px;
            gridline-color: #e1e4e8;
            font-size: 11pt;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QTreeView::item {
            padding: 8px 12px;
            border-bottom: 1px solid #f1f3f4;
            min-height: 20px;
        }
        QTreeView::item:hover {
            background-color: #f1f8ff;
            border-left: 3px solid #0078d4;
        }
        QTreeView::item:selected {
            background-color: #0078d4;
            color: white;
            border-left: 3px solid #106ebe;
        }
        QHeaderView::section {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 #f6f8fa, stop:1 #e1e4e8);
            color: #24292e;
            padding: 12px 15px;
            border: none;
            border-bottom: 2px solid #d1d5da;
            border-right: 1px solid #e1e4e8;
            font-weight: 600;
            font-size: 11pt;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QHeaderView::section:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 #e1e4e8, stop:1 #d1d5da);
        }
        QHeaderView::section:first {
            border-top-left-radius: 6px;
        }
        QHeaderView::section:last {
            border-top-right-radius: 6px;
        }
    """)
    
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Event ID", "Description", "Category", "Provider"])
    tree_view.setModel(model)
    tree_view.setColumnWidth(0, 100)
    tree_view.setColumnWidth(1, 500)
    tree_view.setColumnWidth(2, 180)
    tree_view.setColumnWidth(3, 180)
    main_layout.addWidget(tree_view, 1)
    
    footer_layout = QHBoxLayout()
    footer_label = QLabel("Data source: ")
    footer_link = QLabel("<a href='https://github.com/arimboor/lookups'>arimboor/lookups</a>")
    footer_link.setTextFormat(Qt.RichText)
    footer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
    footer_link.setOpenExternalLinks(True)
    footer_layout.addWidget(footer_label)
    footer_layout.addWidget(footer_link)
    footer_layout.addStretch()
    main_layout.addLayout(footer_layout)
    
    def populate_tree(selected_category, search_term=""):
        model.removeRows(0, model.rowCount())
        try:
            with db_connection(db_path, parent.eventid_window) as conn:
                cursor = conn.cursor()
                if selected_category == "All":
                    if search_term.strip():
                        cursor.execute("""
                            SELECT event_id, description, category, Provider 
                            FROM evtx_id 
                            WHERE event_id LIKE ? 
                            ORDER BY category, event_id
                        """, (f"%{search_term}%",))
                    else:
                        cursor.execute("SELECT event_id, description, category, Provider FROM evtx_id ORDER BY category, event_id")
                else:
                    if search_term.strip():
                        cursor.execute("""
                            SELECT event_id, description, category, Provider 
                            FROM evtx_id 
                            WHERE category = ? AND event_id LIKE ? 
                            ORDER BY event_id
                        """, (selected_category, f"%{search_term}%"))
                    else:
                        cursor.execute("SELECT event_id, description, category, Provider FROM evtx_id WHERE category = ? ORDER BY event_id", (selected_category,))
                rows = cursor.fetchall()
                for row_data in rows:
                    items = [QStandardItem(str(value) if value is not None else "") for value in row_data]
                    model.appendRow(items)
        except Exception as e:
            logger.error(f"Error loading event data: {e}")
            QMessageBox.critical(parent.eventid_window, "Error", f"Failed to load event data: {e}")
        finally:
            for column in range(4):
                tree_view.resizeColumnToContents(column)
    
    def search_events():
        selected_category = category_dropdown.currentText()
        search_term = search_textbox.text()
        populate_tree(selected_category, search_term)
    
    category_dropdown.currentTextChanged.connect(search_events)
    search_textbox.textChanged.connect(search_events)
    populate_tree("All")
    parent.eventid_window.show()
    return parent.eventid_window

@contextmanager
def db_connection(db_path, parent_window=None):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        yield conn
    except sqlite3.Error as e:
        error_msg = f"Database error: {e}"
        logger.error(error_msg)
        if parent_window:
            QMessageBox.critical(parent_window, "Database Error", error_msg)
        raise
    finally:
        if conn:
            conn.close()