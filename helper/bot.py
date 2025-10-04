# code reviewed 
import os
import logging
import yaml
import sqlite3
import openai
import anthropic
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QMessageBox,
    QComboBox, QRadioButton, QButtonGroup, QGroupBox, QGridLayout,
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QTabWidget
)
from PySide6.QtCore import Qt, Slot, QTimer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')
logger = logging.getLogger(__name__)

_bot_window_ref = None

class BotAPIHandler:
    def __init__(self, db_path=None, api_settings=None):
        self.db_path = db_path
        self.api_settings = api_settings or {
            "OpenAI": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7
            },
            "Anthropic": {
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7
            }
        }
        self._api_key_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300
    def get_api_key(self, provider):
        if not self.db_path:
            return None
        current_time = time.time()
        if (current_time - self._cache_timestamp < self._cache_ttl and 
            provider in self._api_key_cache):
            return self._api_key_cache[provider]
        try:
            key_mapping = {
                "OpenAI": "openAI_API_KEY",
                "Anthropic": "ANTHROPIC_API_KEY"
            }
            key_field = key_mapping.get(provider)
            if not key_field:
                return None
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT {key_field} FROM user_settings WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            result = row[0] if row and row[0] else None
            self._api_key_cache[provider] = result
            self._cache_timestamp = current_time
            return result
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving {provider} API key: {e}")
            self._api_key_cache[provider] = None
            self._cache_timestamp = current_time
            return None
    def validate_api_key(self, api_key, provider):
        if not api_key:
            return False
        if provider == "OpenAI":
            return api_key.startswith("sk-") and len(api_key) > 20
        elif provider == "Anthropic":
            return api_key.startswith("sk-ant-") and len(api_key) > 20
        return True
    def call_ai_api(self, messages, max_tokens, selected_llm):
        try:
            logger.info(f"Starting API call for {selected_llm} with {len(messages)} messages")
            api_key = self.get_api_key(selected_llm)
            if not api_key:
                logger.error("API key not configured")
                return None, "API key not configured"
            if not self.validate_api_key(api_key, selected_llm):
                logger.error(f"Invalid {selected_llm} API key format")
                return None, f"Invalid {selected_llm} API key format"
            logger.info(f"Calling {selected_llm} API...")
            if selected_llm == "OpenAI":
                result = self.call_openai_api(messages, max_tokens)
                logger.info("OpenAI API call completed")
                return result, None
            elif selected_llm == "Anthropic":
                result = self.call_anthropic_api(messages, max_tokens)
                logger.info("Anthropic API call completed")
                return result, None
            else:
                logger.error(f"Unsupported provider: {selected_llm}")
                return None, f"Unsupported provider: {selected_llm}"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"API call exception: {error_msg}")
            if "404" in error_msg and "claude" in error_msg.lower():
                return None, "Anthropic model not found. Please check the model name and API version."
            elif "anthropic" in error_msg.lower():
                return None, f"Anthropic API error: {error_msg}"
            elif "openai" in error_msg.lower():
                return None, f"OpenAI API error: {error_msg}"
            else:
                return None, f"API call failed: {error_msg}"
    
    def call_openai_api(self, messages, max_tokens):
        try:
            client = openai.OpenAI(api_key=self.get_api_key("OpenAI"))
            settings = self.api_settings["OpenAI"]
            response = client.chat.completions.create(
                model=settings["model"],
                messages=messages,
                max_tokens=max_tokens,
                temperature=settings["temperature"]
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            raise Exception(f"OpenAI API error: {e}")
        except openai.RateLimitError as e:
            raise Exception(f"OpenAI rate limit exceeded: {e}")
        except openai.APIConnectionError as e:
            raise Exception(f"OpenAI connection error: {e}")
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    def call_anthropic_api(self, messages, max_tokens):
        try:
            client = anthropic.Anthropic(api_key=self.get_api_key("Anthropic"))
            settings = self.api_settings["Anthropic"]
            system_prompt = ""
            user_messages = []
            for message in messages:
                if message["role"] == "system":
                    system_prompt = message["content"]
                else:
                    user_messages.append(message)
            combined_text = ""
            for msg in user_messages:
                if msg["role"] == "user":
                    combined_text += f"User: {msg['content']}\n\n"
                elif msg["role"] == "assistant":
                    combined_text += f"Assistant: {msg['content']}\n\n"
            response = client.messages.create(
                model=settings["model"],
                max_tokens=max_tokens,
                temperature=settings["temperature"],
                system=system_prompt,
                messages=[{"role": "user", "content": combined_text.strip()}]
            )
            return response.content[0].text
        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {e}")
        except anthropic.RateLimitError as e:
            raise Exception(f"Anthropic rate limit exceeded: {e}")
        except anthropic.APIConnectionError as e:
            raise Exception(f"Anthropic connection error: {e}")
        except Exception as e:
            raise Exception(f"Anthropic API call failed: {e}")
    
    def handle_api_error(self, error_message):
        logger.error(f"API Error: {error_message}")
        return f"❌ **Error**: {error_message}\n\nPlease check your API key configuration and try again."
    
    def update_api_settings(self, new_settings):
        self.api_settings.update(new_settings)
    
    def clear_api_key_cache(self):
        self._api_key_cache.clear()
        self._cache_timestamp = 0

class APISettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Settings")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.openai_model = "gpt-3.5-turbo"
        self.openai_temperature = 0.7
        self.anthropic_model = "claude-3-5-sonnet-20241022"
        self.anthropic_temperature = 0.7
        self.max_tokens = 2000
        self.setup_user_interface()
    def setup_user_interface(self):
        layout = QVBoxLayout(self)
        tab_widget = QTabWidget()
        openai_tab = QWidget()
        openai_layout = QFormLayout(openai_tab)
        self.openai_model_combo = QComboBox()
        self.openai_model_combo.addItems([
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k", 
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o"
        ])
        self.openai_model_combo.setCurrentText(self.openai_model)
        openai_layout.addRow("Model:", self.openai_model_combo)
        self.openai_temp_spin = QDoubleSpinBox()
        self.openai_temp_spin.setRange(0.0, 2.0)
        self.openai_temp_spin.setSingleStep(0.1)
        self.openai_temp_spin.setValue(self.openai_temperature)
        self.openai_temp_spin.setDecimals(1)
        openai_layout.addRow("Temperature:", self.openai_temp_spin)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setSingleStep(100)
        self.max_tokens_spin.setValue(self.max_tokens)
        self.max_tokens_spin.setMaximumWidth(120)
        openai_layout.addRow("Max Tokens:", self.max_tokens_spin)
        tab_widget.addTab(openai_tab, "OpenAI")
        anthropic_tab = QWidget()
        anthropic_layout = QFormLayout(anthropic_tab)
        self.anthropic_model_combo = QComboBox()
        self.anthropic_model_combo.addItems([
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ])
        self.anthropic_model_combo.setCurrentText(self.anthropic_model)
        anthropic_layout.addRow("Model:", self.anthropic_model_combo)
        self.anthropic_temp_spin = QDoubleSpinBox()
        self.anthropic_temp_spin.setRange(0.0, 1.0)
        self.anthropic_temp_spin.setSingleStep(0.1)
        self.anthropic_temp_spin.setValue(self.anthropic_temperature)
        self.anthropic_temp_spin.setDecimals(1)
        anthropic_layout.addRow("Temperature:", self.anthropic_temp_spin)
        self.anthropic_max_tokens_spin = QSpinBox()
        self.anthropic_max_tokens_spin.setRange(100, 4000)
        self.anthropic_max_tokens_spin.setSingleStep(100)
        self.anthropic_max_tokens_spin.setValue(self.max_tokens)
        self.anthropic_max_tokens_spin.setMaximumWidth(120)
        anthropic_layout.addRow("Max Tokens:", self.anthropic_max_tokens_spin)
        tab_widget.addTab(anthropic_tab, "Anthropic")
        layout.addWidget(tab_widget)
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    def get_openai_settings(self):
        return {
            "model": self.openai_model_combo.currentText(),
            "temperature": self.openai_temp_spin.value()
        }
    def get_anthropic_settings(self):
        return {
            "model": self.anthropic_model_combo.currentText(),
            "temperature": self.anthropic_temp_spin.value()
        }
    def get_max_tokens(self):
        return self.max_tokens_spin.value()

class ChatBotWindow(QMainWindow):
    def __init__(self, parent=None, db_path=None):
        super().__init__(parent)
        global _bot_window_ref
        _bot_window_ref = self
        self.db_path = db_path
        self._prompts_base_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'llm_prompts')
        self.setWindowTitle("LLM Assistance")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        base_width, base_height = 900, 700
        screen_geometry = QApplication.primaryScreen().geometry()
        x, y = (screen_geometry.width() - base_width) // 2, (screen_geometry.height() - base_height) // 2
        self.setGeometry(x, y, base_width, base_height)
        self.conversation_history = []
        self.selected_llm = "OpenAI"
        self.conversation_mode = True
        self.available_profiles = []
        self.current_profile = None
        self.api_settings = {
            "OpenAI": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7
            },
            "Anthropic": {
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7
            },
            "max_tokens": 2000
        }
        self.api_handler = BotAPIHandler(db_path=self.db_path, api_settings=self.api_settings)
        self.processing_timer = None
        self.processing_dots = 0
        self.api_timeout_timer = None
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #495057;
            }
            QComboBox {
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12pt;
                min-width: 100px;
                color: #212529;
            }
            QComboBox:hover {
                border-color: #007acc;
            }
            QComboBox:focus {
                border-color: #007acc;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                color: #212529;
                background-color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e3f2fd;
                color: #212529;
            }
            QRadioButton {
                font-size: 11pt;
                color: #495057;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator::unchecked {
                border: 2px solid #dee2e6;
                border-radius: 9px;
                background-color: #ffffff;
            }
            QRadioButton::indicator::checked {
                border: 2px solid #007acc;
                border-radius: 9px;
                background-color: #007acc;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 11pt;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border-color: #007acc;
                outline: none;
            }
            QLabel {
                color: #495057;
                font-size: 11pt;
            }
        """)
        self.load_available_profiles()
        if self.available_profiles:
            self.current_profile = self.available_profiles[0]['name']
        self.setup_user_interface()
        self.check_initial_api_status()
    def check_initial_api_status(self):
        if not self.db_path:
            self.status_label.setText("Database not available")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            return
        api_key = self.get_api_key(self.selected_llm)
        if api_key:
            self.update_status_with_context()
        else:
            self.status_label.setText(f"{self.selected_llm} API key not configured")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
    def setup_user_interface(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group)
        config_layout.setSpacing(15)
        llm_label = QLabel("LLM Provider:")
        llm_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.llm_combo = QComboBox()
        self.llm_combo.addItems(["OpenAI", "Anthropic"])
        self.llm_combo.currentTextChanged.connect(self.on_llm_changed)
        self.llm_combo.setMaximumWidth(120)
        config_layout.addWidget(llm_label, 0, 0)
        config_layout.addWidget(self.llm_combo, 0, 1)
        profile_label = QLabel("Select Prompt:")
        profile_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems([profile['name'] for profile in self.available_profiles])
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        self.profile_combo.setFixedWidth(900)
        config_layout.addWidget(profile_label, 0, 2)
        config_layout.addWidget(self.profile_combo, 0, 3)
        config_layout.setColumnStretch(0, 0)
        config_layout.setColumnStretch(1, 0)
        config_layout.setColumnStretch(2, 0)
        config_layout.setColumnStretch(3, 1)
        config_layout.setColumnStretch(4, 0)
        conversation_label = QLabel("Conversation Mode:")
        self.conversation_group = QButtonGroup()
        self.conversation_yes_radio = QRadioButton("Yes (Remember context)")
        self.conversation_no_radio = QRadioButton("No (New question each time)")
        self.conversation_yes_radio.setChecked(True)  
        self.conversation_group.addButton(self.conversation_yes_radio, 0)
        self.conversation_group.addButton(self.conversation_no_radio, 1)
        self.conversation_group.buttonClicked.connect(self.on_conversation_mode_changed)
        conversation_layout = QHBoxLayout()
        conversation_layout.addWidget(self.conversation_yes_radio)
        conversation_layout.addWidget(self.conversation_no_radio)
        conversation_layout.addStretch()
        config_layout.addWidget(conversation_label, 1, 0)
        config_layout.addLayout(conversation_layout, 1, 1, 1, 3)
        main_layout.addWidget(config_group)
        conversation_group = QGroupBox("Conversation")
        conversation_layout = QVBoxLayout(conversation_group)
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        self.conversation_display.setMinimumHeight(300)
        self.conversation_display.setPlaceholderText("Your conversation with the AI will appear here...")
        conversation_layout.addWidget(self.conversation_display)
        input_layout = QHBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(100)
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        input_layout.addWidget(self.message_input)
        conversation_layout.addLayout(input_layout)
        main_layout.addWidget(conversation_group)
        button_frame = QWidget()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 10, 0, 0)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(90)
        self.send_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_conversation)
        self.clear_button.setFixedWidth(90)
        self.clear_button.setToolTip("Clear conversation history (Ctrl+Shift+C)")
        self.clear_button.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.show_api_settings)
        self.settings_button.setFixedWidth(90)
        self.settings_button.setToolTip("API Settings")
        self.settings_button.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        button_layout.addStretch()
        button_layout.addWidget(self.send_button)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.clear_button)
        button_layout.addSpacing(20)
        button_layout.addWidget(self.settings_button)
        button_layout.addStretch()
        main_layout.addWidget(button_frame)
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready to chat")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
    def load_available_profiles(self):
        try:
            profiles_dir = self._prompts_base_path
            self.available_profiles = []
            if os.path.exists(profiles_dir):
                for filename in os.listdir(profiles_dir):
                    if filename.endswith('.yaml') and filename != 'profiles.yaml':
                        profile_path = os.path.join(profiles_dir, filename)
                        try:
                            with open(profile_path, 'r') as f:
                                profile_data = yaml.safe_load(f)
                                if profile_data and 'profile' in profile_data:
                                    profile_info = profile_data['profile']
                                    profile_name = profile_info.get('name', filename.replace('.yaml', '').replace('_', ' ').title())
                                    profile_entry = {
                                        'name': profile_name,
                                        'file': filename,
                                        'id': filename.replace('.yaml', ''),
                                        'description': profile_info.get('metadata', {}).get('focus_areas', ['General assistance']),
                                        'category': profile_info.get('metadata', {}).get('expertise_level', 'general')
                                    }
                                    self.available_profiles.append(profile_entry)
                                    logger.info(f"Loaded profile: {profile_name} from {filename}")
                        except Exception as e:
                            logger.error(f"Error loading profile file {filename}: {e}")
                            continue
            self.available_profiles.sort(key=lambda x: x['name'])
            
            if not self.available_profiles:
                logger.warning("No profiles found, using default profile")
                self.available_profiles = [{'name': 'Generic Assistant', 'file': 'generic.yaml', 'id': 'generic'}]
            
            logger.info(f"Loaded {len(self.available_profiles)} profiles dynamically")
        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
            self.available_profiles = [{'name': 'Generic Assistant', 'file': 'generic.yaml', 'id': 'generic'}]
    def load_profile_prompt(self, profile_name):
        try:
            profile_info = next((p for p in self.available_profiles if p['name'] == profile_name), None)
            if not profile_info:
                logger.error(f"Profile '{profile_name}' not found")
                return self.get_default_prompt()
            
            profile_file = profile_info['file']
            profile_path = os.path.join(self._prompts_base_path, profile_file)
            
            with open(profile_path, 'r') as f:
                profile_data = yaml.safe_load(f)
                if not profile_data or 'profile' not in profile_data:
                    logger.error(f"Invalid profile structure in {profile_file}")
                    return self.get_default_prompt()
                
                prompt_data = profile_data.get('profile', {}).get('prompt', {})
                system_message = prompt_data.get('system_message', '')
                role_specific = prompt_data.get('role_specific', '')
                
                if role_specific:
                    full_prompt = f"{system_message}\n\n{role_specific}"
                else:
                    full_prompt = system_message
                
                logger.info(f"Loaded prompt for '{profile_name}' from {profile_file}")
                return full_prompt
        except FileNotFoundError:
            logger.error(f"Profile file for '{profile_name}' not found: {profile_file}")
            return self.get_default_prompt()
        except Exception as e:
            logger.error(f"Error loading profile '{profile_name}': {e}")
            return self.get_default_prompt()
    def get_default_prompt(self):
        return "You are a helpful AI assistant with broad knowledge across various domains. Provide clear, accurate, and helpful responses to user queries."
    def on_profile_changed(self, profile_name):
        self.current_profile = profile_name
        self.status_label.setText(f"Prompt changed to: {profile_name}")
        self.status_label.setStyleSheet("color: #007acc; font-weight: bold;")
        QTimer.singleShot(2000, lambda: self.update_status_with_context())
        logger.info(f"Prompt changed to: {profile_name}")
    def get_api_key(self, provider):
        return self.api_handler.get_api_key(provider)
    @Slot()
    def on_llm_changed(self, llm_name):
        self.selected_llm = llm_name
        api_key = self.get_api_key(llm_name)
        if api_key:
            self.status_label.setText(f"Switched to {llm_name} ✓")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.status_label.setText(f"Switched to {llm_name} - API key not configured")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        QTimer.singleShot(3000, lambda: self.update_status_with_context())
    @Slot()
    def on_conversation_mode_changed(self, button):
        if button == self.conversation_yes_radio:
            self.conversation_mode = True
            mode_text = "Conversational mode enabled"
            mode_color = "#28a745"
        else:
            self.conversation_mode = False
            mode_text = "New question mode enabled"
            mode_color = "#ffc107"
        self.status_label.setText(mode_text)
        self.status_label.setStyleSheet(f"color: {mode_color}; font-weight: bold;")
        QTimer.singleShot(3000, lambda: self.update_status_with_context())
    def update_status_with_context(self):
        if self.conversation_mode:
            context_info = self.get_conversation_context_info()
            if context_info['has_context']:
                self.status_label.setText(f"Ready to chat (Context: {context_info['user_messages']} exchanges)")
            else:
                self.status_label.setText("Ready to chat (Conversational mode)")
        else:
            self.status_label.setText("Ready to chat (New question mode)")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
    @Slot()
    def send_message(self):
        message = self.message_input.toPlainText().strip()
        if not message:
            self.status_label.setText("Please enter a message")
            self.status_label.setStyleSheet("color: #ffc107; font-weight: bold;")
            QTimer.singleShot(2000, lambda: self.update_status_with_context())
            return
        if len(message) > 4000:
            QMessageBox.warning(self, "Message Too Long", 
                              "Message is too long. Please keep it under 4000 characters.")
            return
        api_key = self.get_api_key(self.selected_llm)
        if not api_key:
            QMessageBox.warning(self, "API Key Missing", 
                              f"{self.selected_llm} API key is not configured.\n\n"
                              "Please configure your API key in the main application's API Settings.")
            return
        self.conversation_history.append(message)
        self.message_input.clear()
        self.status_label.setText("Sending message...")
        self.status_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        self.send_button.setEnabled(False)
        QTimer.singleShot(1500, self.simulate_ai_response)
    def call_ai_api(self, messages, max_tokens=1000):
        response, error = self.api_handler.call_ai_api(messages, max_tokens, self.selected_llm)
        if error:
            self.handle_api_error(error)
            return None
        return response
    def simulate_ai_response(self):
        try:
            if self.current_profile:
                system_prompt = self.load_profile_prompt(self.current_profile)
                logger.info(f"Using prompt: {self.current_profile}")
            else:
                system_prompt = self.get_default_prompt()
                logger.info("Using default prompt")
            messages = [{"role": "system", "content": system_prompt}]
            if self.conversation_mode:
                self.manage_conversation_context()
                for i, message in enumerate(self.conversation_history):
                    if i % 2 == 0:
                        messages.append({"role": "user", "content": message})
                    else:
                        messages.append({"role": "assistant", "content": message})
                context_info = self.get_conversation_context_info()
                logger.info(f"Conversational mode ({self.selected_llm}): {context_info['user_messages']} user messages, {context_info['assistant_messages']} assistant messages")
            else:
                current_message = self.conversation_history[-1] if self.conversation_history else "Hello"
                messages.append({"role": "user", "content": current_message})
                logger.info(f"New question mode ({self.selected_llm}): sending only current message without context")
            max_tokens = self.api_settings["max_tokens"]
            logger.info(f"Starting API call with {len(messages)} messages, max_tokens: {max_tokens}")
            self.start_processing_indicator()
            self.start_api_timeout()
            
            QTimer.singleShot(100, lambda: self.call_api_async(messages, max_tokens))
        except Exception as e:
            logger.error(f"Error in _simulate_ai_response: {e}")
            self.handle_api_error(f"Unexpected error: {str(e)}")
            self.send_button.setEnabled(True)
    def call_api_async(self, messages, max_tokens):
        try:
            logger.info("Starting async API call")
            api_key = self.get_api_key(self.selected_llm)
            logger.info(f"API key available: {api_key is not None}")
            
            if not api_key:
                logger.error("No API key found")
                self.handle_api_error("API key not configured")
                return
            
            logger.info("Calling actual API...")
            ai_response = self.call_ai_api(messages, max_tokens=max_tokens)
            logger.info(f"API response received: {ai_response is not None}")
            
            if ai_response:
                self.conversation_history.append(ai_response)
                self.update_ui_with_response(ai_response)
                logger.info("API response added to UI")
            else:
                logger.warning("API returned None response")
                self.handle_api_error("No response received from API")
                
        except Exception as e:
            logger.error(f"Error in async API call: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.handle_api_error(f"API call failed: {str(e)}")
    
    
    def update_ui_with_response(self, ai_response):
        self.stop_processing_indicator()
        self.stop_api_timeout()
        self.add_message_to_conversation("AI Assistant", ai_response)
        self.update_status_with_context()
        self.enable_send_button()
    
    def enable_send_button(self):
        self.send_button.setEnabled(True)
    
    def start_processing_indicator(self):
        self.processing_dots = 0
        self.status_label.setText("Processing... Please wait")
        self.status_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self.update_processing_dots)
        self.processing_timer.start(500)
    
    def update_processing_dots(self):
        self.processing_dots = (self.processing_dots + 1) % 4
        dots = "." * self.processing_dots
        self.status_label.setText(f"Processing{dots} Please wait")
    
    def stop_processing_indicator(self):
        if self.processing_timer:
            self.processing_timer.stop()
            self.processing_timer = None
    
    def start_api_timeout(self):
        self.api_timeout_timer = QTimer()
        self.api_timeout_timer.timeout.connect(self.handle_api_timeout)
        self.api_timeout_timer.setSingleShot(True)
        self.api_timeout_timer.start(30000)
    
    def handle_api_timeout(self):
        logger.error("API call timed out after 30 seconds")
        self.stop_processing_indicator()
        self.handle_api_error("API call timed out after 30 seconds. Please check your internet connection and try again.")
        self.enable_send_button()
    
    def stop_api_timeout(self):
        if self.api_timeout_timer:
            self.api_timeout_timer.stop()
            self.api_timeout_timer = None
    def handle_api_error(self, error_message):
        self.stop_processing_indicator()
        self.stop_api_timeout()
        error_response = self.api_handler.handle_api_error(error_message)
        self.add_message_to_conversation("AI Assistant", error_response)
        self.status_label.setText("Error occurred")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.send_button.setEnabled(True)
    def manage_conversation_context(self, max_messages=20):
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]
            logger.info(f"Trimmed conversation history to last {max_messages} messages")
    def get_conversation_context_info(self):
        total_messages = len(self.conversation_history)
        user_messages = len([msg for i, msg in enumerate(self.conversation_history) if i % 2 == 0])
        assistant_messages = len([msg for i, msg in enumerate(self.conversation_history) if i % 2 == 1])
        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "has_context": total_messages > 0
        }
    def add_message_to_conversation(self, sender, message):
        if sender == "You":
            formatted_message = f"<div style='margin: 10px 0; padding: 10px; background-color: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;'>"
            formatted_message += f"<strong>You:</strong><br>{message.replace(chr(10), '<br>')}"
        else:
            formatted_message = f"<div style='margin: 10px 0; padding: 10px; background-color: #f3e5f5; border-radius: 8px; border-left: 4px solid #9c27b0;'>"
            formatted_message += f"<strong>AI Assistant:</strong><br>{message.replace(chr(10), '<br>')}"
        formatted_message += "</div>"
        self.conversation_display.append(formatted_message)
        scrollbar = self.conversation_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    @Slot()
    def clear_conversation(self):
        if not self.conversation_history and self.conversation_display.toPlainText().strip() == "":
            self.status_label.setText("Nothing to clear")
            self.status_label.setStyleSheet("color: #ffc107; font-weight: bold;")
            QTimer.singleShot(2000, lambda: self.update_status_with_context())
            return
        self.conversation_display.clear()
        self.conversation_history = []
        self.status_label.setText("Conversation cleared")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        QTimer.singleShot(2000, lambda: self.update_status_with_context())
        logger.info("Conversation cleared by user")
    @Slot()
    def show_api_settings(self):
        dialog = APISettingsDialog(self)
        dialog.openai_model_combo.setCurrentText(self.api_settings["OpenAI"]["model"])
        dialog.openai_temp_spin.setValue(self.api_settings["OpenAI"]["temperature"])
        dialog.anthropic_model_combo.setCurrentText(self.api_settings["Anthropic"]["model"])
        dialog.anthropic_temp_spin.setValue(self.api_settings["Anthropic"]["temperature"])
        dialog.max_tokens_spin.setValue(self.api_settings["max_tokens"])
        dialog.anthropic_max_tokens_spin.setValue(self.api_settings["max_tokens"])
        if dialog.exec() == QDialog.Accepted:
            self.api_settings["OpenAI"] = dialog.get_openai_settings()
            self.api_settings["Anthropic"] = dialog.get_anthropic_settings()
            self.api_settings["max_tokens"] = dialog.get_max_tokens()
            self.api_handler.update_api_settings(self.api_settings)
            self.api_handler.clear_api_key_cache()
            self.status_label.setText("API settings updated")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            QTimer.singleShot(2000, lambda: self.update_status_with_context())
    def closeEvent(self, event):
        self.stop_processing_indicator()
        self.stop_api_timeout()
        event.accept()
        global _bot_window_ref
        _bot_window_ref = None

def handle_chat_bot(parent=None, db_path=None):
    global _bot_window_ref
    if _bot_window_ref is not None and not _bot_window_ref.isHidden():
        _bot_window_ref.raise_()
        _bot_window_ref.activateWindow()
        return _bot_window_ref
    bot_window = ChatBotWindow(parent, db_path)
    bot_window.setAttribute(Qt.WA_DeleteOnClose, True)
    bot_window.show()
    _bot_window_ref = bot_window
    return bot_window