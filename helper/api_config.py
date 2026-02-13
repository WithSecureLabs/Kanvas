# API configuration for Kanvas: load/save API keys from api.yaml and provide
# the API Settings dialog for users to manage keys (VT, Shodan, OTX, HIBP, etc.).
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import os

import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from helper import styles

logger = logging.getLogger(__name__)

API_YAML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "api.yaml"
)

API_KEY_FIELDS = [
    "VT_API_KEY",
    "SHODEN_API_KEY",
    "OTX_API_KEY",
    "MISP_API_KEY",
    "OpenCTI_API_KEY",
    "IPQS_API_KEY",
    "openAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "HIBP_API_KEY",
    "urlscan_API_KEY",
    "vulners_API_KEY",
    "malpedia_API_KEY",
    "URLhaus_API_KEY",
    "HudonRock_API_KEY",
]

API_SETTINGS_DISPLAY_FIELDS = [
    "VT_API_KEY",
    "SHODEN_API_KEY",
    "OTX_API_KEY",
    "MISP_API_KEY",
    "OpenCTI_API_KEY",
    "IPQS_API_KEY",
    "openAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "HIBP_API_KEY",
]

API_FIELD_LABELS = [
    ("VirusTotal :", "VT_API_KEY"),
    ("Shodan.io :", "SHODEN_API_KEY"),
    ("AlienVault OTX :", "OTX_API_KEY"),
    ("IP Quality Score :", "IPQS_API_KEY"),
    ("OpenAI :", "openAI_API_KEY"),
    ("Anthropic :", "ANTHROPIC_API_KEY"),
    ("Have I Been Pwned :", "HIBP_API_KEY"),
]


def get_api_key(key_field):
    try:
        with open(API_YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "api_keys" in data and key_field in data["api_keys"]:
            value = data["api_keys"][key_field]
            if value and str(value).strip():
                return str(value).strip()
        return None
    except (yaml.YAMLError, OSError) as e:
        logger.error("Error reading API key %s: %s", key_field, e)
        return None


def load_api_keys():
    try:
        with open(API_YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "api_keys" in data:
            return data["api_keys"]
        return {}
    except (yaml.YAMLError, OSError) as e:
        logger.error("Error loading API keys: %s", e)
        return {}


def save_api_keys(api_keys):
    try:
        data = {"api_keys": api_keys}
        with open(API_YAML_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        return True
    except (yaml.YAMLError, OSError) as e:
        logger.error("Error saving API keys: %s", e)
        return False


def mask_api_key(api_key):
    if not api_key or api_key.strip() == "":
        return ""
    if len(api_key) <= 8:
        return "****"
    return api_key[:4] + "*" * (len(api_key) - 4)


def open_api_settings(parent_window, logger_instance, child_windows):
    custom_window = QWidget(parent_window)
    custom_window.setWindowTitle("API Settings")
    custom_window.setMinimumSize(800, 400)
    custom_window.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowCloseButtonHint
        | Qt.WindowMinimizeButtonHint
    )
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(20, 20, 20, 20)
    current_settings = {}

    try:
        api_keys = load_api_keys()
        for name in API_SETTINGS_DISPLAY_FIELDS:
            value = api_keys.get(name) or ""
            if value is None:
                value = ""
            value = str(value).strip()
            current_settings[name] = {
                "original": value,
                "masked": mask_api_key(value),
            }
        if not api_keys:
            logger_instance.info("No settings found in api.yaml")
    except Exception as e:
        logger_instance.error("Error loading settings: %s", e)
        QMessageBox.critical(
            custom_window, "Error", f"Failed to fetch settings: {e}"
        )
        for field in API_SETTINGS_DISPLAY_FIELDS:
            current_settings[field] = {"original": "", "masked": ""}

    scroll_widget = QWidget()
    scroll_layout = QGridLayout(scroll_widget)
    scroll_layout.setColumnStretch(1, 1)
    input_fields = {}
    for row, (label_text, field_name) in enumerate(API_FIELD_LABELS):
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        scroll_layout.addWidget(label, row, 0)
        input_field = QLineEdit()
        input_field.setMinimumWidth(350)
        input_field.setEchoMode(QLineEdit.Password)
        original_value = current_settings.get(field_name, {}).get(
            "original", ""
        )
        if original_value:
            input_field.setText(original_value)
            input_field.setPlaceholderText(
                current_settings[field_name]["masked"]
            )
        scroll_layout.addWidget(input_field, row, 1)
        show_button = QPushButton("Show")
        show_button.setFixedWidth(60)
        show_button.setStyleSheet(styles.BUTTON_SHOW_PADDING)

        def make_toggle(field, button):
            def toggle_visibility():
                if field.echoMode() == QLineEdit.Password:
                    field.setEchoMode(QLineEdit.Normal)
                    button.setText("Hide")
                else:
                    field.setEchoMode(QLineEdit.Password)
                    button.setText("Show")

            return toggle_visibility

        show_button.clicked.connect(
            make_toggle(input_field, show_button)
        )
        scroll_layout.addWidget(show_button, row, 2)
        input_fields[field_name] = input_field

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setWidget(scroll_widget)
    main_layout.addWidget(scroll_area)

    button_layout = QHBoxLayout()
    button_layout.addStretch(1)
    update_button = QPushButton("Update")
    update_button.setStyleSheet(styles.BUTTON_UPDATE)
    button_layout.addWidget(update_button)
    cancel_button = QPushButton("Cancel")
    cancel_button.setStyleSheet(styles.BUTTON_PADDING_ONLY)
    button_layout.addWidget(cancel_button)
    main_layout.addSpacing(15)
    main_layout.addLayout(button_layout)
    custom_window.setLayout(main_layout)

    def save_settings():
        try:
            existing = load_api_keys()
            for field_name, input_field in input_fields.items():
                existing[field_name] = input_field.text().strip()
            if save_api_keys(existing):
                QMessageBox.information(
                    custom_window, "Success", "Settings saved successfully!"
                )
                custom_window.close()
            else:
                QMessageBox.critical(
                    custom_window, "Error", "Failed to save settings."
                )
        except Exception as e:
            logger_instance.error("Error saving settings: %s", e)
            QMessageBox.critical(
                custom_window, "Error", f"Failed to save settings: {e}"
            )

    update_button.clicked.connect(save_settings)
    cancel_button.clicked.connect(custom_window.close)
    child_windows.append(custom_window)
    custom_window.show()
