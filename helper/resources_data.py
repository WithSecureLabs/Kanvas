"""
Knowledge-base data windows for Kanvas: Microsoft/Entra portals browser and
Windows Event ID lookup. Loads data from the app database and provides search/filter.
Revised on 01/02/2026 by Jinto Antony
"""

import logging
import sqlite3
import webbrowser
from collections import defaultdict
from contextlib import contextmanager

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from helper import styles

logger = logging.getLogger(__name__)

GOV_KEYWORDS = frozenset(("us gov", "gcc", "dod", "china"))
AI_KEYWORDS = frozenset(("ai", "copilot", "intelligence", "cortana"))
SEC_KEYWORDS = frozenset(("security", "defender", "compliance"))
M365_KEYWORDS = frozenset(("365", "office", "teams", "sharepoint", "exchange", "outlook", "word", "excel", "powerpoint"))
DEV_KEYWORDS = frozenset(("dev", "developer", "studio", "visual", "code"))
LIC_KEYWORDS = frozenset(("licensing", "pricing", "subscription"))
PARTNER_KEYWORDS = frozenset(("partner", "trial", "msp"))


NO_DATA_MSG = "No data found. Please click 'Download Updates' to download the latest files."


def _has_msportals_data(db_path):
    if not db_path:
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookmarks'")
        if not cursor.fetchone():
            return False
        cursor.execute("SELECT 1 FROM bookmarks WHERE group_name LIKE '%Microsoft%' OR group_name LIKE '%Azure%' LIMIT 1")
        has_row = cursor.fetchone() is not None
        conn.close()
        return has_row
    except Exception:
        return False


def _has_event_id_data(db_path):
    if not db_path:
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evtx_id'")
        if not cursor.fetchone():
            conn.close()
            return False
        cursor.execute("SELECT 1 FROM evtx_id LIMIT 1")
        has_row = cursor.fetchone() is not None
        conn.close()
        return has_row
    except Exception:
        return False


def display_msportals_data(parent, db_path):
    if getattr(parent, "msportals_window", None) is not None and parent.msportals_window.isVisible():
        parent.msportals_window.raise_()
        parent.msportals_window.activateWindow()
        return parent.msportals_window
    if getattr(parent, "msportals_window", None) is not None:
        parent.msportals_window = None
    if not _has_msportals_data(db_path):
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
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
        logger.error("Failed to populate msportals data: %s", e)


def categorize_portal(group_name, portal_name):
    name_lower = portal_name.lower()
    group_lower = group_name.lower()

    if any(g in group_lower for g in GOV_KEYWORDS):
        return "Government Clouds"
    if any(k in name_lower for k in AI_KEYWORDS):
        return "AI & Intelligence"
    if any(k in name_lower for k in SEC_KEYWORDS):
        return "Security & Compliance"
    if "azure" in name_lower or "azure" in group_lower:
        return "Azure Services"
    if any(k in name_lower for k in M365_KEYWORDS):
        return "Microsoft 365"
    if any(k in name_lower for k in DEV_KEYWORDS):
        return "Development Tools"
    if "admin" in name_lower or "admin" in group_lower:
        return "Admin Centers"
    if any(k in name_lower for k in LIC_KEYWORDS):
        return "Licensing & Pricing"
    if any(k in group_lower for k in PARTNER_KEYWORDS):
        return "Partner & Trials"
    if "non-microsoft" in group_lower or "3rd party" in group_lower:
        return "Third-Party Tools"
    if "end user" in group_lower:
        return "End User Portals"
    return "Other"


def filter_tree(tree_widget, search_text):
    search_lower = search_text.lower()
    for i in range(tree_widget.topLevelItemCount()):
        category_item = tree_widget.topLevelItem(i)
        category_visible = False
        for j in range(category_item.childCount()):
            portal_item = category_item.child(j)
            if search_lower in portal_item.text(0).lower() or search_lower in portal_item.text(1).lower():
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
    if getattr(parent, "eventid_window", None) is not None and parent.eventid_window.isVisible():
        parent.eventid_window.raise_()
        parent.eventid_window.activateWindow()
        return parent.eventid_window
    if getattr(parent, "eventid_window", None) is not None:
        parent.eventid_window = None
    if not _has_event_id_data(db_path):
        QMessageBox.information(parent.window, "No Data", NO_DATA_MSG)
        return None
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
                logger.info("Found %s categories: %s", len(db_categories), db_categories)
    except Exception as e:
        logger.error("Error fetching categories: %s", e)
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
    tree_view.setStyleSheet(styles.TREE_VIEW_EVENT_ID_STYLE)

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
                        cursor.execute(
                            "SELECT event_id, description, category, Provider FROM evtx_id WHERE event_id LIKE ? ORDER BY category, event_id",
                            (f"%{search_term}%",),
                        )
                    else:
                        cursor.execute("SELECT event_id, description, category, Provider FROM evtx_id ORDER BY category, event_id")
                else:
                    if search_term.strip():
                        cursor.execute(
                            "SELECT event_id, description, category, Provider FROM evtx_id WHERE category = ? AND event_id LIKE ? ORDER BY event_id",
                            (selected_category, f"%{search_term}%"),
                        )
                    else:
                        cursor.execute("SELECT event_id, description, category, Provider FROM evtx_id WHERE category = ? ORDER BY event_id", (selected_category,))
                rows = cursor.fetchall()
                for row_data in rows:
                    items = [QStandardItem(str(value) if value is not None else "") for value in row_data]
                    model.appendRow(items)
        except Exception as e:
            logger.error("Error loading event data: %s", e)
            QMessageBox.critical(parent.eventid_window, "Error", f"Failed to load event data: {e}")
        finally:
            for column in range(4):
                tree_view.resizeColumnToContents(column)

    def search_events():
        populate_tree(category_dropdown.currentText(), search_textbox.text())

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
        logger.error("Database error: %s", e)
        if parent_window:
            QMessageBox.critical(parent_window, "Database Error", error_msg)
        raise
    finally:
        if conn:
            conn.close()
