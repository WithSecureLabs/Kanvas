# Bookmarks Knowledge Base for Kanvas: display and manage bookmark categories from
# the database, with add/modify/delete for Personal bookmarks; data sourced from oneTracker.org.
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import sqlite3
from collections import defaultdict
from contextlib import contextmanager

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

PERSONAL_GROUP = "Personal"
EXCLUDED_GROUP = "Microsoft Portals via msportals.io"
BOOKMARKS_TABLE = "bookmarks"
DROPDOWN_WIDTH = 273
DIALOG_WIDTH = 400
DIALOG_HEIGHT = 150
ONETRACKER_URL = "https://onetracker.org/tools"


@contextmanager
def db_connection(db_path, parent_window=None):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        yield conn
    except sqlite3.Error as e:
        logger.error("Database error: %s", e)
        if parent_window:
            QMessageBox.critical(
                parent_window, "Database Error", f"Database error: {e}"
            )
        raise
    finally:
        if conn:
            conn.close()


def fetch_group_names(db_path, parent_window=None):
    try:
        with db_connection(db_path, parent_window) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT group_name FROM {BOOKMARKS_TABLE} "
                "ORDER BY group_name"
            )
            groups = [
                row[0] for row in cursor.fetchall()
                if row[0] and row[0] != EXCLUDED_GROUP
            ]
            logger.info(
                "Retrieved %d groups (excluding Microsoft Portals): %s",
                len(groups),
                groups,
            )
            return groups
    except sqlite3.Error as e:
        logger.error("Failed to fetch group names: %s", e)
        return []


def sort_groups_with_personal_first(group_names):
    if PERSONAL_GROUP in group_names:
        result = [PERSONAL_GROUP]
        for g in group_names:
            if g != PERSONAL_GROUP:
                result.append(g)
        return result
    return group_names


def display_bookmarks_kb(parent, db_path):
    if hasattr(parent, "bookmarks_window") and parent.bookmarks_window is not None:
        parent.bookmarks_window.raise_()
        parent.bookmarks_window.activateWindow()
        return parent.bookmarks_window

    group_names = fetch_group_names(db_path, parent.window)
    sorted_group_names = sort_groups_with_personal_first(group_names)

    parent.bookmarks_window = QWidget(parent.window)
    parent.bookmarks_window.setWindowTitle("Bookmarks")
    parent.bookmarks_window.resize(960, 780)
    parent.bookmarks_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )
    parent.bookmarks_window.closeEvent = lambda event: reset_bookmarks_window(
        parent, event
    )

    main_layout = QVBoxLayout(parent.bookmarks_window)
    main_layout.setSpacing(0)
    main_layout.setContentsMargins(10, 5, 10, 5)

    top_frame = QWidget()
    top_frame.setMaximumHeight(30)
    top_layout = QHBoxLayout(top_frame)
    top_layout.setContentsMargins(5, 0, 5, 0)
    top_layout.setSpacing(5)

    group_label = QLabel("Category:")
    top_layout.addWidget(group_label)

    group_dropdown = QComboBox()
    group_dropdown.addItems(sorted_group_names)
    group_dropdown.setFixedWidth(DROPDOWN_WIDTH)
    if PERSONAL_GROUP in sorted_group_names:
        group_dropdown.setCurrentIndex(
            sorted_group_names.index(PERSONAL_GROUP)
        )
    top_layout.addWidget(group_dropdown)
    top_layout.addStretch()

    add_btn = QPushButton("Add")
    modify_btn = QPushButton("Modify")
    delete_btn = QPushButton("Delete")
    top_layout.addWidget(add_btn)
    top_layout.addWidget(modify_btn)
    top_layout.addWidget(delete_btn)
    main_layout.addWidget(top_frame)

    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setSpacing(0)
    content_layout.setContentsMargins(5, 0, 5, 0)
    content_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll_area.setWidget(content_widget)
    main_layout.addWidget(scroll_area, 1)

    current_bookmarks = []

    def display_bookmarks(selected_group):
        nonlocal current_bookmarks
        while content_layout.count():
            child = content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        try:
            with db_connection(db_path, parent.bookmarks_window) as conn:
                cursor = conn.cursor()
                if selected_group:
                    cursor.execute(
                        f"SELECT group_name, portal_name, primary_url FROM "
                        f"{BOOKMARKS_TABLE} WHERE group_name = ? "
                        "ORDER BY portal_name",
                        (selected_group,),
                    )
                else:
                    cursor.execute(
                        f"SELECT group_name, portal_name, primary_url FROM "
                        f"{BOOKMARKS_TABLE} ORDER BY group_name, portal_name"
                    )
                rows = cursor.fetchall()
                current_bookmarks = rows
                logger.info("Retrieved %d bookmarks for display", len(rows))
        except sqlite3.Error as e:
            logger.error("Failed to retrieve bookmarks: %s", e)
            current_bookmarks = []
            return

        is_personal = selected_group == PERSONAL_GROUP
        add_btn.setEnabled(is_personal)
        modify_btn.setEnabled(is_personal)
        delete_btn.setEnabled(is_personal)

        bookmarks_by_group = defaultdict(list)
        for group_name, bookmark_name, url in rows:
            bookmarks_by_group[group_name].append((bookmark_name, url))

        for group_idx, group_name in enumerate(
            sorted(bookmarks_by_group.keys())
        ):
            group_header = QLabel(group_name)
            font = QFont()
            font.setBold(True)
            font.setPointSize(11)
            group_header.setFont(font)
            group_header.setContentsMargins(0, 0, 0, 0)
            content_layout.addWidget(group_header)

            spacing_widget = QWidget()
            spacing_widget.setFixedHeight(10)
            content_layout.addWidget(spacing_widget)

            for bookmark_name, url in bookmarks_by_group[group_name]:
                link_widget = QWidget()
                link_layout = QHBoxLayout(link_widget)
                link_layout.setContentsMargins(5, 0, 5, 0)
                link_layout.setSpacing(2)
                name_label = QLabel(f"{bookmark_name}:")
                name_label.setSizePolicy(
                    QSizePolicy.Fixed, QSizePolicy.Fixed
                )
                link_layout.addWidget(name_label)
                clean_url = url.rstrip(",")
                url_label = QLabel(
                    f"<a href='{clean_url}'>{clean_url}</a>"
                )
                url_label.setTextFormat(Qt.RichText)
                url_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                url_label.setOpenExternalLinks(True)
                link_layout.addWidget(url_label)
                link_widget.setMaximumHeight(18)
                content_layout.addWidget(link_widget)

            if group_idx < len(bookmarks_by_group) - 1:
                separator = QWidget()
                separator.setFixedHeight(12)
                content_layout.addWidget(separator)

    def add_bookmark():
        if group_dropdown.currentText() != PERSONAL_GROUP:
            logger.warning(
                "Attempted to add bookmark to non-Personal group"
            )
            QMessageBox.warning(
                parent.bookmarks_window,
                "Cannot Add",
                f"You can only add bookmarks to the '{PERSONAL_GROUP}' group",
            )
            return
        dialog = QDialog(parent.bookmarks_window)
        dialog.setWindowTitle("Add New Bookmark")
        dialog.setFixedSize(DIALOG_WIDTH, DIALOG_HEIGHT)
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        url_edit = QLineEdit()
        layout.addRow("Bookmark Name:", name_edit)
        layout.addRow("URL:", url_edit)
        button_box = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(save_btn)
        button_box.addWidget(cancel_btn)
        layout.addRow("", button_box)
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            url = url_edit.text().strip()
            if not name or not url:
                QMessageBox.warning(
                    parent.bookmarks_window,
                    "Invalid Input",
                    "Both name and URL are required",
                )
                return
            try:
                with db_connection(
                    db_path, parent.bookmarks_window
                ) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"INSERT INTO {BOOKMARKS_TABLE} "
                        "(group_name, portal_name, primary_url) VALUES (?, ?, ?)",
                        (PERSONAL_GROUP, name, url),
                    )
                    conn.commit()
                    QMessageBox.information(
                        parent.bookmarks_window,
                        "Success",
                        "Bookmark added successfully",
                    )
                    display_bookmarks(PERSONAL_GROUP)
            except sqlite3.Error as e:
                logger.error("Failed to add bookmark: %s", e)

    def modify_bookmark():
        if group_dropdown.currentText() != PERSONAL_GROUP:
            QMessageBox.warning(
                parent.bookmarks_window,
                "Cannot Modify",
                f"You can only modify bookmarks in the '{PERSONAL_GROUP}' group",
            )
            return
        personal_bookmarks = [
            (name, url)
            for group, name, url in current_bookmarks
            if group == PERSONAL_GROUP
        ]
        if not personal_bookmarks:
            QMessageBox.information(
                parent.bookmarks_window,
                "No Bookmarks",
                "No Personal bookmarks to modify",
            )
            return
        selection_dialog = QDialog(parent.bookmarks_window)
        selection_dialog.setWindowTitle("Select Bookmark to Modify")
        selection_dialog.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        selection_layout = QVBoxLayout(selection_dialog)
        bookmark_combo = QComboBox()
        bookmark_combo.addItems([n for n, _ in personal_bookmarks])
        selection_layout.addWidget(
            QLabel("Select a bookmark to modify:")
        )
        selection_layout.addWidget(bookmark_combo)
        button_box = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(select_btn)
        button_box.addWidget(cancel_btn)
        selection_layout.addLayout(button_box)
        select_btn.clicked.connect(selection_dialog.accept)
        cancel_btn.clicked.connect(selection_dialog.reject)
        if selection_dialog.exec() != QDialog.Accepted:
            return
        selected_idx = bookmark_combo.currentIndex()
        if selected_idx < 0:
            return
        old_name, old_url = personal_bookmarks[selected_idx]
        edit_dialog = QDialog(parent.bookmarks_window)
        edit_dialog.setWindowTitle("Modify Bookmark")
        edit_dialog.setFixedSize(DIALOG_WIDTH, DIALOG_HEIGHT)
        edit_layout = QFormLayout(edit_dialog)
        name_edit = QLineEdit(old_name)
        url_edit = QLineEdit(old_url)
        edit_layout.addRow("Bookmark Name:", name_edit)
        edit_layout.addRow("URL:", url_edit)
        button_box = QHBoxLayout()
        update_btn = QPushButton("Update")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(update_btn)
        button_box.addWidget(cancel_btn)
        edit_layout.addRow("", button_box)
        update_btn.clicked.connect(edit_dialog.accept)
        cancel_btn.clicked.connect(edit_dialog.reject)
        if edit_dialog.exec() == QDialog.Accepted:
            name = name_edit.text().strip()
            url = url_edit.text().strip()
            if not name or not url:
                QMessageBox.warning(
                    parent.bookmarks_window,
                    "Invalid Input",
                    "Both name and URL are required",
                )
                return
            try:
                with db_connection(
                    db_path, parent.bookmarks_window
                ) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"UPDATE {BOOKMARKS_TABLE} SET portal_name = ?, "
                        "primary_url = ? WHERE group_name = ? AND portal_name = ?",
                        (name, url, PERSONAL_GROUP, old_name),
                    )
                    conn.commit()
                    QMessageBox.information(
                        parent.bookmarks_window,
                        "Success",
                        "Bookmark updated successfully",
                    )
                    display_bookmarks(PERSONAL_GROUP)
            except sqlite3.Error as e:
                logger.error("Failed to modify bookmark: %s", e)

    def delete_bookmark():
        if group_dropdown.currentText() != PERSONAL_GROUP:
            QMessageBox.warning(
                parent.bookmarks_window,
                "Cannot Delete",
                f"You can only delete bookmarks in the '{PERSONAL_GROUP}' group",
            )
            return
        personal_bookmarks = [
            (name, url)
            for group, name, url in current_bookmarks
            if group == PERSONAL_GROUP
        ]
        if not personal_bookmarks:
            QMessageBox.information(
                parent.bookmarks_window,
                "No Bookmarks",
                "No Personal bookmarks to delete",
            )
            return
        selection_dialog = QDialog(parent.bookmarks_window)
        selection_dialog.setWindowTitle("Delete Bookmark")
        selection_dialog.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        selection_layout = QVBoxLayout(selection_dialog)
        bookmark_combo = QComboBox()
        bookmark_combo.addItems([n for n, _ in personal_bookmarks])
        selection_layout.addWidget(
            QLabel("Select a bookmark to delete:")
        )
        selection_layout.addWidget(bookmark_combo)
        button_box = QHBoxLayout()
        delete_btn = QPushButton("Delete")
        cancel_btn = QPushButton("Cancel")
        button_box.addWidget(delete_btn)
        button_box.addWidget(cancel_btn)
        selection_layout.addLayout(button_box)
        delete_btn.clicked.connect(selection_dialog.accept)
        cancel_btn.clicked.connect(selection_dialog.reject)
        if selection_dialog.exec() != QDialog.Accepted:
            return
        selected_idx = bookmark_combo.currentIndex()
        if selected_idx < 0:
            return
        selected_name = personal_bookmarks[selected_idx][0]
        confirm = QMessageBox.question(
            parent.bookmarks_window,
            "Confirm Deletion",
            f"Are you sure you want to delete '{selected_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                with db_connection(
                    db_path, parent.bookmarks_window
                ) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"DELETE FROM {BOOKMARKS_TABLE} WHERE group_name = ? "
                        "AND portal_name = ?",
                        (PERSONAL_GROUP, selected_name),
                    )
                    conn.commit()
                    logger.info(
                        "Bookmark '%s' deleted successfully",
                        selected_name,
                    )
                    QMessageBox.information(
                        parent.bookmarks_window,
                        "Success",
                        "Bookmark deleted successfully",
                    )
                    display_bookmarks(PERSONAL_GROUP)
            except sqlite3.Error as e:
                logger.error("Failed to delete bookmark: %s", e)

    group_dropdown.currentTextChanged.connect(display_bookmarks)
    add_btn.clicked.connect(add_bookmark)
    modify_btn.clicked.connect(modify_bookmark)
    delete_btn.clicked.connect(delete_bookmark)

    footer_frame = QWidget()
    footer_layout = QHBoxLayout(footer_frame)
    footer_layout.setContentsMargins(10, 0, 10, 2)
    footer_layout.setSpacing(0)
    info_label = QLabel("The data obtained from ")
    footer_layout.addWidget(info_label)
    link_label = QLabel(
        f"<a href='{ONETRACKER_URL}'>oneTracker.org</a>"
    )
    link_label.setTextFormat(Qt.RichText)
    link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    link_label.setOpenExternalLinks(True)
    footer_layout.addWidget(link_label)
    footer_layout.addStretch()
    main_layout.addWidget(footer_frame)

    if sorted_group_names:
        if PERSONAL_GROUP in sorted_group_names:
            display_bookmarks(PERSONAL_GROUP)
        else:
            display_bookmarks(sorted_group_names[0])
    else:
        display_bookmarks("")

    parent.bookmarks_window.show()
    return parent.bookmarks_window


def reset_bookmarks_window(parent, event):
    parent.bookmarks_window = None
    event.accept()
