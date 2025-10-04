import os
import sys
import logging
import platform
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                               QPushButton, QLabel, QMessageBox, QApplication, 
                               QTextEdit, QSplitter, QFileDialog)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence, QIcon, QFont

class MitreFlowWindowBase(QMainWindow):
    def __init__(self, parent=None, platform_config=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.platform_config = platform_config or {}
        self.download_in_progress = False
        self.current_download = None
        self.logger.info(f"MitreFlowWindowBase initialized for {platform.system()}")
        self.setup_platform_environment()
        self.setup_ui()
        self.setup_web_view()
        
    def setup_platform_environment(self):
        env_vars = self.platform_config.get('environment', {})
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Set environment variable: {key}={value}")
    
    def setup_ui(self):
        platform_name = platform.system()
        self.setWindowTitle(f"MITRE Attack Flow Builder")
        self.setGeometry(100, 100, 1200, 800)
        try:
            icon_path = "images/icon.ico"
            self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            self.logger.warning(f"Could not load window icon: {e}")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        main_layout.addLayout(self.create_header_layout())
        main_layout.addWidget(self.create_web_view_splitter())
        main_layout.addWidget(self.create_status_label())
        self.setup_shortcuts()
        
    def create_header_layout(self):
        header_layout = QHBoxLayout()
        title_label = QLabel(f"MITRE Attack Flow Builder")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin: 5px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet(self._get_button_style("#3498db", "#2980b9", "#21618c"))
        refresh_button.clicked.connect(self.refresh_page)
        header_layout.addWidget(refresh_button)
        close_button = QPushButton("Close")
        close_button.setStyleSheet(self._get_button_style("#e74c3c", "#c0392b", "#a93226"))
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)
        return header_layout
    
    def create_web_view_splitter(self):
        splitter = QSplitter(Qt.Vertical)
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("""
            QWebEngineView {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
        """)
        splitter.addWidget(self.web_view)
        self.console_widget = self.create_console_widget()
        splitter.addWidget(self.console_widget)
        splitter.setSizes([800, 200])
        return splitter
    
    def create_console_widget(self):
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        console_layout.setContentsMargins(5, 5, 5, 5)
        console_label = QLabel("Debug Console (F12 to toggle)")
        console_label.setStyleSheet("color: #7f8c8d; font-weight: bold; margin-bottom: 5px;")
        console_layout.addWidget(console_label)
        self.console_text = QTextEdit()
        self.console_text.setMaximumHeight(150)
        self.console_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        self.console_text.setReadOnly(True)
        console_layout.addWidget(self.console_text)
        console_widget.hide()
        return console_widget
    
    def create_status_label(self):
        self.status_label = QLabel("Loading MITRE Attack Flow...")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic; margin: 5px;")
        return self.status_label
    
    def _get_button_style(self, bg_color, hover_color, pressed_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """
    
    def setup_shortcuts(self):
        shortcuts = [
            ("F12", self.toggle_console),
            ("F5", self.refresh_page),
            ("Ctrl+R", self.refresh_page),
            ("Ctrl+Shift+F", self.ensure_window_visible)
        ]
        for key_sequence, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.activated.connect(handler)
    
    def toggle_console(self):
        if self.console_widget.isVisible():
            self.console_widget.hide()
        else:
            self.console_widget.show()
    
    def log_to_console(self, message):
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.console_text.append(formatted_message)
            self.console_text.verticalScrollBar().setValue(
                self.console_text.verticalScrollBar().maximum()
            )
        except Exception as e:
            self.logger.error(f"Error logging to console: {e}")
    
    def setup_web_view(self):
        try:
            url = "https://center-for-threat-informed-defense.github.io/attack-flow/ui/"
            self.logger.info(f"Setting up web view with URL: {url}")
            self.configure_web_settings()
            self.web_view.load(QUrl(url))
            self.web_view.loadStarted.connect(self.on_load_started)
            self.web_view.loadFinished.connect(self.on_load_finished)
            self.web_view.loadProgress.connect(self.on_load_progress)
            self.setup_download_handling()
            QTimer.singleShot(10000, self.check_page_load_timeout)
        except Exception as e:
            self.logger.error(f"Error setting up web view: {e}")
            self.show_error_message(f"Failed to initialize web browser: {str(e)}")
    
    def configure_web_settings(self):
        page = self.web_view.page()
        settings = page.settings()
        web_attributes = self.platform_config.get('web_attributes', {})
        for attribute, value in web_attributes.items():
            try:
                if hasattr(settings.WebAttribute, attribute):
                    attr = getattr(settings.WebAttribute, attribute)
                    settings.setAttribute(attr, value)
                else:
                    self.logger.warning(f"Unknown web attribute: {attribute}")
            except Exception as e:
                self.logger.warning(f"Could not set WebAttribute {attribute}: {e}")
        settings.setDefaultTextEncoding("utf-8")
        try:
            profile = page.profile()
            user_agent = self.platform_config.get('user_agent')
            if user_agent:
                profile.setHttpUserAgent(user_agent)
        except Exception as e:
            self.logger.warning(f"Could not set user agent: {e}")
    
    def setup_download_handling(self):
        try:
            self.web_view.page().profile().downloadRequested.connect(self.handle_download)
            self.logger.info("Download handler connected successfully")
            self.log_to_console("Download handler connected successfully")
        except Exception as e:
            self.logger.warning(f"Download handler not available: {e}")
            self.log_to_console(f"Download handler not available: {e}")
    
    def check_page_load_timeout(self):
        try:
            if self.status_label.text().startswith("Loading MITRE Attack Flow"):
                self.logger.warning("Page load timeout - page may not be loading properly")
                self.log_to_console("Page load timeout - page may not be loading properly")
                self.status_label.setText("Page load timeout - check internet connection")
                self.status_label.setStyleSheet("color: #e74c3c; font-style: italic; margin: 5px;")
                self.offer_browser_fallback("Page failed to load within timeout period.")
        except Exception as e:
            self.logger.error(f"Error in page load timeout check: {e}")
    
    def on_load_started(self):
        self.logger.info("Page load started")
        self.status_label.setText("Loading MITRE Attack Flow...")
        self.status_label.setStyleSheet("color: #f39c12; font-style: italic; margin: 5px;")
        self.log_to_console("Page load started")
    
    def on_load_progress(self, progress):
        self.logger.debug(f"Page load progress: {progress}%")
        self.status_label.setText(f"Loading MITRE Attack Flow... {progress}%")
        self.status_label.setStyleSheet("color: #f39c12; font-style: italic; margin: 5px;")
    
    def on_load_finished(self, success):
        if success:
            self.logger.info("Page loaded successfully")
            self.status_label.setText("MITRE Attack Flow loaded successfully")
            self.status_label.setStyleSheet("color: #27ae60; font-style: italic; margin: 5px;")
            self.log_to_console("Page loaded successfully")
            QTimer.singleShot(1000, self.inject_enhancement_script)
        else:
            self.logger.error("Page load failed")
            self.status_label.setText("Failed to load MITRE Attack Flow")
            self.status_label.setStyleSheet("color: #e74c3c; font-style: italic; margin: 5px;")
            self.log_to_console("Error loading page")
            self.show_error_page()
    
    def show_error_page(self):
        error_html = """
        <h1>Error loading page</h1>
        <p>Could not load MITRE Attack Flow UI</p>
        <p>Check your internet connection, firewall, or QtWebEngine installation.</p>
        """
        self.web_view.setHtml(error_html)
        self.logger.error("Displayed error page to user")
    
    def inject_enhancement_script(self):
        try:
            enhancement_script = f"""
            (function() {{
                console.log('MITRE Attack Flow Enhancement Script Loaded ({platform.system()})');
                document.addEventListener('click', function(event) {{
                    try {{
                        const target = event.target;
                        if (target && target.textContent) {{
                            const text = target.textContent.toLowerCase();
                            if (text.includes('save') || text.includes('export')) {{
                                console.log('Save/Export action detected:', text);
                            }}
                        }}
                    }} catch (e) {{
                        console.error('Error in click handler:', e.message);
                    }}
                }});
            }})();
            """
            self.web_view.page().runJavaScript(enhancement_script)
        except Exception as e:
            self.logger.error(f"Error injecting enhancement script: {e}")
    
    def refresh_page(self):
        try:
            self.status_label.setText("Refreshing page...")
            self.status_label.setStyleSheet("color: #f39c12; font-style: italic; margin: 5px;")
            self.web_view.reload()
        except Exception as e:
            self.logger.error(f"Error refreshing page: {e}")
            self.show_error_message(f"Failed to refresh page: {str(e)}")
    
    def handle_download(self, download_item):
        try:
            suggested_filename = download_item.suggestedFileName()
            if not suggested_filename:
                suggested_filename = "mitre_attack_flow_export"
            self.raise_()
            self.activateWindow()
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Save MITRE Attack Flow File",
                suggested_filename,
                "MITRE Attack Flow (*.afb);;All Files (*);;JSON Files (*.json);;Text Files (*.txt);;XML Files (*.xml)"
            )
            self.raise_()
            self.activateWindow()
            if file_path:
                final_path = self.process_download_path(file_path, suggested_filename)
                download_item.setDownloadFileName(final_path)
                self.download_in_progress = True
                self.current_download = download_item
                QTimer.singleShot(1000, self.check_download_status)
                download_item.accept()
                self.status_label.setText(f"Downloading to: {final_path}")
                self.status_label.setStyleSheet("color: #27ae60; font-style: italic; margin: 5px;")
                self.log_to_console(f"Download started: {suggested_filename} -> {final_path}")
            else:
                download_item.cancel()
                self.log_to_console("Download cancelled by user")
        except Exception as e:
            self.logger.error(f"Error handling download: {e}")
            self.log_to_console(f"Download error: {str(e)}")
            try:
                download_item.cancel()
            except:
                pass
            self.show_error_message(f"Failed to save file: {str(e)}")
    
    def process_download_path(self, file_path, suggested_filename):
        if platform.system() == "Windows":
            if suggested_filename.endswith('.afb') and not file_path.endswith(('.afb', '.json', '.txt', '.xml')):
                if not file_path.endswith('.afb'):
                    file_path = file_path + '.afb'
        return file_path
    
    def check_download_status(self):
        try:
            if self.current_download and self.download_in_progress:
                if hasattr(self.current_download, 'isFinished') and self.current_download.isFinished():
                    self.on_download_finished()
                else:
                    QTimer.singleShot(500, self.check_download_status)
            else:
                self.download_in_progress = False
                self.current_download = None
        except Exception as e:
            self.logger.error(f"Error checking download status: {e}")
            self.log_to_console(f"Download status check error: {str(e)}")
            self.download_in_progress = False
            self.current_download = None
    
    def on_download_finished(self):
        try:
            self.download_in_progress = False
            self.current_download = None
            self.status_label.setText("Download completed successfully")
            self.status_label.setStyleSheet("color: #27ae60; font-style: italic; margin: 5px;")
            self.log_to_console("Download completed successfully")
            self.raise_()
            self.activateWindow()
            QTimer.singleShot(3000, self.reset_status)
        except Exception as e:
            self.logger.error(f"Error in download finished handler: {e}")
            self.log_to_console(f"Download finished error: {str(e)}")
            self.download_in_progress = False
            self.current_download = None
    
    def reset_status(self):
        self.status_label.setText("MITRE Attack Flow loaded successfully")
        self.status_label.setStyleSheet("color: #27ae60; font-style: italic; margin: 5px;")
    
    def ensure_window_visible(self):
        try:
            self.show()
            self.raise_()
            self.activateWindow()
            self.log_to_console("Window brought to front")
        except Exception as e:
            self.logger.error(f"Error ensuring window visibility: {e}")
    
    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)
    
    def offer_browser_fallback(self, error_message):
        try:
            reply = QMessageBox.question(
                self, 
                "Web View Failed", 
                f"{error_message}\n\n"
                "Would you like to open MITRE Attack Flow in your system browser instead?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if self.open_in_system_browser():
                    QMessageBox.information(self, "Opened in Browser", "MITRE Attack Flow opened in your system browser.")
                    self.close()
                else:
                    QMessageBox.critical(self, "Browser Error", "Failed to open system browser.")
        except Exception as e:
            self.logger.error(f"Error in browser fallback offer: {e}")
    
    def open_in_system_browser(self, url="https://center-for-threat-informed-defense.github.io/attack-flow/ui/"):
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            self.logger.error(f"Failed to open system browser: {e}")
            return False
    
    def closeEvent(self, event):
        try:
            self.logger.info("Window close event triggered")
            self.log_to_console("Window close event triggered")
            if self.download_in_progress:
                self.logger.warning("Download in progress - preventing close")
                self.log_to_console("Download in progress - preventing close")
                reply = QMessageBox.question(
                    self, 
                    "Download in Progress", 
                    "A download is currently in progress. Are you sure you want to close the window?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    event.ignore()
                    return
            if hasattr(self, 'web_view'):
                self.web_view.stop()
            if hasattr(self, 'web_view') and self.web_view.page():
                try:
                    profile = self.web_view.page().profile()
                    if hasattr(profile, 'downloadRequested'):
                        signal = profile.downloadRequested
                        if signal.receivers() > 0:
                            signal.disconnect()
                except Exception as e:
                    self.logger.warning(f"Error cleaning up downloads: {e}")
            self.download_in_progress = False
            self.current_download = None
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during close: {e}")
            event.accept()