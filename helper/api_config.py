# code reviewed 
import sqlite3
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QScrollArea, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

def open_api_settings(parent_window, db_path, logger, child_windows):
    custom_window = QWidget(parent_window)
    custom_window.setWindowTitle("API Settings")
    custom_window.setMinimumSize(800, 400)
    custom_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(20, 20, 20, 20)
    current_settings = {}
    
    def mask_api_key(api_key):
        if not api_key or api_key.strip() == "":
            return ""
        if len(api_key) <= 8:
            return "****"
        return api_key[:4] + "*" * (len(api_key) - 4)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT VT_API_KEY, SHODEN_API_KEY, OTX_API_KEY, MISP_API_KEY, OpenCTI_API_KEY, IPQS_API_KEY, openAI_API_KEY, ANTHROPIC_API_KEY, HIBP_API_KEY FROM user_settings WHERE id = 1")
        row = cursor.fetchone()
        if row:
            field_names = ['VT_API_KEY', 'SHODEN_API_KEY', 'OTX_API_KEY', 'MISP_API_KEY', 'OpenCTI_API_KEY', 'IPQS_API_KEY', 'openAI_API_KEY', 'ANTHROPIC_API_KEY', 'HIBP_API_KEY']
            for i, name in enumerate(field_names):
                current_settings[name] = {
                    'original': row[i] if row[i] is not None else "",
                    'masked': mask_api_key(row[i] if row[i] is not None else "")
                }
        else:
            logger.info("No settings found in database")
            for field in [
                'VT_API_KEY', 'SHODEN_API_KEY', 'OTX_API_KEY', 'MISP_API_KEY',
                'OpenCTI_API_KEY', 'IPQS_API_KEY', 'openAI_API_KEY', 'ANTHROPIC_API_KEY', 'HIBP_API_KEY'
            ]:
                current_settings[field] = {'original': "", 'masked': ""}
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        QMessageBox.critical(custom_window, "Error", f"Failed to fetch settings: {e}")
        for field in [
            'VT_API_KEY', 'SHODEN_API_KEY', 'OTX_API_KEY', 'MISP_API_KEY',
            'OpenCTI_API_KEY', 'IPQS_API_KEY', 'openAI_API_KEY', 'ANTHROPIC_API_KEY', 'HIBP_API_KEY'
        ]:
            current_settings[field] = {'original': "", 'masked': ""}
    finally:
        if 'conn' in locals():
            conn.close()
    scroll_widget = QWidget()
    scroll_layout = QGridLayout(scroll_widget)
    scroll_layout.setColumnStretch(1, 1)
    api_fields = [
        ("VirusTotal :", "VT_API_KEY"),
        ("Shodan.io :", "SHODEN_API_KEY"),
        ("AlienVault OTX :", "OTX_API_KEY"),
        ("IP Quality Score :", "IPQS_API_KEY"),
        ("OpenAI :", "openAI_API_KEY"),
        ("Anthropic :", "ANTHROPIC_API_KEY"),
        ("Have I Been Pwned :", "HIBP_API_KEY")
    ]
    input_fields = {}
    show_buttons = {}
    for row, (label_text, field_name) in enumerate(api_fields):
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        scroll_layout.addWidget(label, row, 0)
        input_field = QLineEdit()
        input_field.setMinimumWidth(350)
        input_field.setEchoMode(QLineEdit.Password)
        original_value = current_settings.get(field_name, {}).get('original', '')
        if original_value:
            input_field.setText(original_value)
            input_field.setPlaceholderText(current_settings[field_name]['masked'])
        scroll_layout.addWidget(input_field, row, 1)
        show_button = QPushButton("Show")
        show_button.setFixedWidth(60)
        show_button.setStyleSheet("padding: 4px 8px;")
        
        def create_toggle_function(field, button):
            def toggle_visibility():
                if field.echoMode() == QLineEdit.Password:
                    field.setEchoMode(QLineEdit.Normal)
                    button.setText("Hide")
                else:
                    field.setEchoMode(QLineEdit.Password)
                    button.setText("Show")
            return toggle_visibility
        show_button.clicked.connect(create_toggle_function(input_field, show_button))
        scroll_layout.addWidget(show_button, row, 2)
        input_fields[field_name] = input_field
        show_buttons[field_name] = show_button
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(scroll_widget)
    main_layout.addWidget(scroll_area)
    button_layout = QHBoxLayout()
    button_layout.addStretch(1)
    update_button = QPushButton("Update")
    update_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px 20px;")
    button_layout.addWidget(update_button)
    cancel_button = QPushButton("Cancel")
    cancel_button.setStyleSheet("padding: 6px 20px;")
    button_layout.addWidget(cancel_button)
    main_layout.addSpacing(15)
    main_layout.addLayout(button_layout)
    custom_window.setLayout(main_layout)

    def save_settings():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            update_fields = []
            values = []
            for field_name, input_field in input_fields.items():
                update_fields.append(f"{field_name} = ?")
                api_key_value = input_field.text().strip()
                values.append(api_key_value)
            query = f"UPDATE user_settings SET {', '.join(update_fields)} WHERE id = 1"
            cursor.execute(query, values)
            if cursor.rowcount == 0:
                field_names = list(input_fields.keys())
                placeholders = ", ".join(["?"] * len(field_names))
                field_str = ", ".join(field_names)
                query = f"INSERT INTO user_settings (id, {field_str}) VALUES (1, {placeholders})"
                cursor.execute(query, values)
            conn.commit()
            QMessageBox.information(custom_window, "Success", "Settings saved successfully!")
            custom_window.close()
        except sqlite3.Error as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(custom_window, "Error", f"Failed to save settings: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    update_button.clicked.connect(save_settings)
    cancel_button.clicked.connect(custom_window.close)
    child_windows.append(custom_window)
    custom_window.show()
