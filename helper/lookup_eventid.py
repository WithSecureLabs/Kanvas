import sqlite3
import traceback
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QTreeView, QScrollArea, QPushButton, QSizePolicy, QMessageBox
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

def display_event_id_kb(parent, db_path):
    kb_window = QWidget(parent.window)  
    kb_window.setWindowTitle("Event ID Knowledge Base")
    kb_window.resize(1000, 500)  
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(5)
    main_layout.setContentsMargins(10, 10, 10, 10)
    title_label = QLabel("Event ID Lookup")
    title_font = QFont()
    title_font.setPointSize(14)
    title_font.setBold(True)
    title_label.setFont(title_font)
    title_label.setAlignment(Qt.AlignCenter)
    main_layout.addWidget(title_label)
    filter_frame = QWidget()
    filter_layout = QHBoxLayout(filter_frame)
    filter_layout.setContentsMargins(0, 5, 0, 5)
    category_label = QLabel("Category:")
    category_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    filter_layout.addWidget(category_label)
    categories = ["All"]
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evtx_id'")
        if not cursor.fetchone():
            QMessageBox.warning(kb_window, "Missing Data", "The Event ID database table (evtx_id) does not exist. Please run the update function to create it.")
        else:
            cursor.execute("SELECT DISTINCT category FROM evtx_id")
            db_categories = [row[0] for row in cursor.fetchall() if row[0]]
            categories.extend(sorted(db_categories))
            logger.info(f"Found {len(db_categories)} categories: {db_categories}")
    except sqlite3.Error as e:
        logger.error(f"Error fetching categories: {e}")
        QMessageBox.critical(kb_window, "Error", f"Failed to fetch categories: {e}")
        #traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()
    category_dropdown = QComboBox()
    category_dropdown.addItems(categories)
    category_dropdown.setFixedWidth(250)
    filter_layout.addWidget(category_dropdown)
    filter_layout.addStretch()
    main_layout.addWidget(filter_frame)
    tree_view = QTreeView()
    tree_view.setRootIsDecorated(False)  
    tree_view.setAlternatingRowColors(True)
    tree_view.setSelectionBehavior(QTreeView.SelectRows)
    tree_view.setSortingEnabled(True)
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Event ID", "Description", "Category", "Provider"])
    tree_view.setModel(model)
    tree_view.setColumnWidth(0, 100)  
    tree_view.setColumnWidth(1, 500)  
    tree_view.setColumnWidth(2, 180)  
    tree_view.setColumnWidth(3, 180)  
    main_layout.addWidget(tree_view, 1) 
    button_frame = QWidget()
    button_layout = QHBoxLayout(button_frame)
    button_layout.setContentsMargins(0, 5, 0, 0)
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet("background-color: #4CAF50; color: white;")
    close_button.clicked.connect(kb_window.close)
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addWidget(button_frame)
    
    def populate_tree(selected_category):
        model.removeRows(0, model.rowCount())
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            if selected_category == "All":
                cursor.execute("SELECT event_id, description, category, Provider FROM evtx_id ORDER BY category, event_id")
            else:
                cursor.execute("SELECT event_id, description, category, Provider FROM evtx_id WHERE category = ? ORDER BY event_id", (selected_category,))
            rows = cursor.fetchall()
            for row_data in rows:
                items = [QStandardItem(str(value) if value is not None else "") for value in row_data]
                model.appendRow(items)
        except sqlite3.Error as e:
            logger.error(f"Error loading event data: {e}")
            QMessageBox.critical(kb_window, "Error", f"Failed to load event data: {e}")
            #traceback.print_exc()
        finally:
            if 'conn' in locals():
                conn.close()
    category_dropdown.currentTextChanged.connect(populate_tree)
    populate_tree("All")
    kb_window.show() 
    return kb_window