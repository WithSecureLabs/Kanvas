# MITRE Attack Flow - merged module (config, core, utils, windows, platform)
# Order: config -> core -> utils -> windows -> platform

import os
import sys
import logging
import platform
import webbrowser
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QMessageBox, QApplication, QTextEdit, QSplitter, QFileDialog
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence, QIcon, QFont

from helper import styles

# ---------------------------------------------------------------------------
# Section 1: Config (mitre_flow_config)
# ---------------------------------------------------------------------------

PLATFORM_CONFIGS = {
    'windows': {
        'environment': {
            'QTWEBENGINE_DISABLE_SANDBOX': '1',
            'QTWEBENGINE_CHROMIUM_FLAGS': '--disable-gpu --disable-web-security --disable-features=VizDisplayCompositor',
            'QT_AUTO_SCREEN_SCALE_FACTOR': '1',
            'QT_SCALE_FACTOR': '1'
        },
        'web_attributes': {
            'JavascriptEnabled': True,
            'LocalContentCanAccessRemoteUrls': True,
            'LocalContentCanAccessFileUrls': True,
            'AllowRunningInsecureContent': True,
            'JavascriptCanOpenWindows': True,
            'JavascriptCanAccessClipboard': True,
            'LocalStorageEnabled': True,
            'WebGLEnabled': True
        },
        'user_agent': 'Mozilla/5.0 (compatible; QtWebEngine; MITRE Attack Flow Client)',
        'dependencies': [
            'Visual C++ Redistributable 2015-2022 (x64)',
            'Chrome/Edge browser',
            'QtWebEngineProcess.exe'
        ],
        'error_messages': {
            'import_error': """
            QtWebEngine not available on Windows.

            Solutions:
            1. Install Visual C++ Redistributable 2015-2022 (x64)
            2. Use conda: conda install pyside6-qtwebengine
            3. Download pre-built wheels from PyPI
            4. Check Windows Defender exclusions

            Note: 32-bit Windows not supported. Windows Defender may block execution.
            """,
            'runtime_error': """
            QtWebEngine runtime error on Windows.

            Common causes:
            - Missing Visual C++ Redistributable (x64)
            - Windows Defender blocking QtWebEngineProcess.exe
            - Missing Chrome/Chromium dependencies
            - Graphics driver issues
            - High DPI scaling issues

            Solutions:
            1. Add QtWebEngineProcess.exe to Windows Defender exclusions
            2. Run as administrator
            3. Update graphics drivers
            4. Check for malware disguised as QtWebEngineProcess.exe
            """
        }
    },
    'linux': {
        'environment': {
            'QTWEBENGINE_DISABLE_SANDBOX': '1',
            'QTWEBENGINE_CHROMIUM_FLAGS': '--disable-gpu --disable-web-security --disable-features=VizDisplayCompositor --no-sandbox --disable-dev-shm-usage',
            'QT_AUTO_SCREEN_SCALE_FACTOR': '1',
            'QT_SCALE_FACTOR': '1'
        },
        'web_attributes': {
            'JavascriptEnabled': True,
            'LocalContentCanAccessRemoteUrls': True,
            'LocalContentCanAccessFileUrls': True,
            'AllowRunningInsecureContent': True,
            'JavascriptCanOpenWindows': True,
            'JavascriptCanAccessClipboard': True,
            'LocalStorageEnabled': True,
            'WebGLEnabled': True
        },
        'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'dependencies': [
            'python3-pyside6.qtwebengine',
            'libxcb libraries',
            'QtWebEngineProcess'
        ],
        'error_messages': {
            'import_error': """
            QtWebEngine not available on Linux.

            Solutions:
            Ubuntu/Debian: sudo apt install python3-pyside6.qtwebengine
            CentOS/RHEL: sudo yum install qt5-qtwebengine-devel
            Arch: sudo pacman -S pyside6-qtwebengine

            Note: Use system package manager instead of pip.
            """,
            'runtime_error': """
            QtWebEngine runtime error on Linux.

            Common causes:
            - Missing system libraries
            - Graphics driver issues
            - Wayland vs X11 problems

            Try: export QT_QPA_PLATFORM=xcb
            """
        }
    },
    'macos': {
        'environment': {
            'QTWEBENGINE_DISABLE_SANDBOX': '1'
        },
        'web_attributes': {
            'JavascriptEnabled': True,
            'LocalContentCanAccessRemoteUrls': True,
            'LocalContentCanAccessFileUrls': True,
            'AllowRunningInsecureContent': True,
            'JavascriptCanOpenWindows': True,
            'JavascriptCanAccessClipboard': True,
            'LocalStorageEnabled': True,
            'WebGLEnabled': True
        },
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'dependencies': [
            'pyside6-qtwebengine',
            'Code signing (for distribution)'
        ],
        'error_messages': {
            'import_error': """
            QtWebEngine not available on macOS.

            Solutions:
            1. Install via conda: conda install pyside6-qtwebengine
            2. Install via Homebrew: brew install pyside6
            3. For Apple Silicon: May need Rosetta 2

            Note: Code signing may be required for distribution.
            """,
            'runtime_error': """
            QtWebEngine runtime error on macOS.

            Common causes:
            - Sandboxing restrictions
            - Missing entitlements
            - Graphics driver issues

            Try running with: --disable-web-security
            """
        }
    }
}

def get_platform_config():
    system = platform.system().lower()
    if system == 'darwin':
        return PLATFORM_CONFIGS['macos']
    elif system == 'windows':
        return PLATFORM_CONFIGS['windows']
    elif system == 'linux':
        return PLATFORM_CONFIGS['linux']
    else:
        return PLATFORM_CONFIGS['linux']

def get_platform_error_message(error_type):
    config = get_platform_config()
    return config['error_messages'].get(error_type, "Unknown platform error")

def get_platform_dependencies():
    config = get_platform_config()
    return config['dependencies']

def setup_platform_environment():
    config = get_platform_config()
    environment = config.get('environment', {})
    for key, value in environment.items():
        os.environ[key] = value

def check_platform_specific_issues():
    system = platform.system().lower()
    issues = []
    if system == 'windows':
        issues.extend(check_windows_issues())
    elif system == 'linux':
        issues.extend(check_linux_issues())
    elif system == 'darwin':
        issues.extend(check_macos_issues())
    return issues

def check_windows_issues():
    issues = []
    try:
        try:
            result = subprocess.run(['reg', 'query', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                issues.append("Visual C++ Redistributable 2015-2022 (x64) not found")
        except Exception:
            issues.append("Cannot check Visual C++ Redistributable status")
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), "QtWebEngineProcess.exe"),
            os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "PySide6", "QtWebEngineProcess.exe"),
            os.path.join(os.path.dirname(sys.executable), "Library", "bin", "QtWebEngineProcess.exe")
        ]
        qtwebengine_found = False
        for path in possible_paths:
            if os.path.exists(path):
                qtwebengine_found = True
                break
        if not qtwebengine_found:
            issues.append("QtWebEngineProcess.exe not found in expected locations")
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
        chrome_found = False
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_found = True
                break
        if not chrome_found:
            issues.append("No Chrome/Edge browser found - may affect QtWebEngine functionality")
    except Exception as e:
        issues.append(f"Error checking Windows dependencies: {e}")
    return issues

def check_linux_issues():
    issues = []
    try:
        package_checks = [
            ("libxcb-xinerama0", "X11 Xinerama extension"),
            ("libxcb-cursor0", "X11 cursor library"),
            ("libxcb-icccm4", "X11 ICCCM library"),
            ("libxcb-image0", "X11 image library"),
            ("libxcb-keysyms1", "X11 keysyms library"),
            ("libxcb-randr0", "X11 RandR extension"),
            ("libxcb-render-util0", "X11 render utilities"),
            ("libxcb-shape0", "X11 shape extension"),
            ("libxcb-xfixes0", "X11 XFixes extension"),
            ("libxcb-xkb1", "X11 XKB library")
        ]
        for pkg, description in package_checks:
            try:
                result = subprocess.run(['dpkg', '-l', pkg],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    issues.append(f"{pkg} ({description}) not found")
            except Exception:
                break
        qtwebengine_paths = [
            "/usr/lib/x86_64-linux-gnu/qt6/libexec/QtWebEngineProcess",
            "/usr/lib/qt6/libexec/QtWebEngineProcess",
            "/usr/local/lib/qt6/libexec/QtWebEngineProcess"
        ]
        qtwebengine_found = any(os.path.exists(p) for p in qtwebengine_paths)
        if not qtwebengine_found:
            issues.append("QtWebEngineProcess not found in expected locations")
        if 'WAYLAND_DISPLAY' in os.environ and 'QT_QPA_PLATFORM' not in os.environ:
            issues.append("Wayland detected but QT_QPA_PLATFORM not set to xcb")
    except Exception as e:
        issues.append(f"Error checking Linux dependencies: {e}")
    return issues

def check_macos_issues():
    issues = []
    try:
        if platform.machine() == "arm64":
            issues.append("Apple Silicon compatibility issues may occur")
        if not os.path.exists("/Applications/Xcode.app"):
            issues.append("Xcode not found - code signing may be required for distribution")
    except Exception as e:
        issues.append(f"Error checking macOS dependencies: {e}")
    return issues

# ---------------------------------------------------------------------------
# Section 2: Core (mitre_flow_core)
# ---------------------------------------------------------------------------

class MitreFlowWindowBase(QMainWindow):
    def __init__(self, parent=None, platform_config=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.platform_config = platform_config or {}
        self.download_in_progress = False
        self.current_download = None
        self.web_view_initialized = False
        self.logger.info(f"MitreFlowWindowBase initialized for {platform.system()}")
        self.setup_platform_environment()
        self.setup_ui()

    def setup_platform_environment(self):
        env_vars = self.platform_config.get('environment', {})
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Set environment variable: {key}={value}")

    def setup_ui(self):
        self.setWindowTitle("MITRE Attack Flow Builder")
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
        title_label = QLabel("MITRE Attack Flow Builder")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(styles.LABEL_TITLE_DARK)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet(styles.BUTTON_STYLE_REFRESH)
        refresh_button.clicked.connect(self.refresh_page)
        header_layout.addWidget(refresh_button)
        close_button = QPushButton("Close")
        close_button.setStyleSheet(styles.BUTTON_STYLE_CLOSE_RED)
        close_button.clicked.connect(self.close)
        header_layout.addWidget(close_button)
        return header_layout

    def create_web_view_splitter(self):
        splitter = QSplitter(Qt.Vertical)
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet(styles.WEB_ENGINE_VIEW_STYLE)
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
        console_label.setStyleSheet(styles.CONSOLE_LABEL_STYLE)
        console_layout.addWidget(console_label)
        self.console_text = QTextEdit()
        self.console_text.setMaximumHeight(150)
        self.console_text.setStyleSheet(styles.CONSOLE_TEXT_EDIT_STYLE)
        self.console_text.setReadOnly(True)
        console_layout.addWidget(self.console_text)
        console_widget.hide()
        return console_widget

    def create_status_label(self):
        self.status_label = QLabel("Loading MITRE Attack Flow...")
        self.status_label.setStyleSheet(styles.STATUS_LABEL_DEFAULT)
        return self.status_label

    def setup_shortcuts(self):
        for key_sequence, handler in [
            ("F12", self.toggle_console),
            ("F5", self.refresh_page),
            ("Ctrl+R", self.refresh_page),
            ("Ctrl+Shift+F", self.ensure_window_visible)
        ]:
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
        if self.web_view_initialized:
            return
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
            self.web_view_initialized = True
        except Exception as e:
            self.logger.error(f"Error setting up web view: {e}")
            self.show_error_message(f"Failed to initialize web browser: {str(e)}")

    def showEvent(self, event):
        super().showEvent(event)
        if not self.web_view_initialized:
            QTimer.singleShot(100, self.setup_web_view)

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
                self.status_label.setStyleSheet(styles.STATUS_LABEL_ERROR)
                self.offer_browser_fallback("Page failed to load within timeout period.")
        except Exception as e:
            self.logger.error(f"Error in page load timeout check: {e}")

    def on_load_started(self):
        self.logger.info("Page load started")
        self.status_label.setText("Loading MITRE Attack Flow...")
        self.status_label.setStyleSheet(styles.STATUS_LABEL_WARNING)
        self.log_to_console("Page load started")

    def on_load_progress(self, progress):
        self.logger.debug(f"Page load progress: {progress}%")
        self.status_label.setText(f"Loading MITRE Attack Flow... {progress}%")
        self.status_label.setStyleSheet(styles.STATUS_LABEL_WARNING)

    def on_load_finished(self, success):
        if success:
            self.logger.info("Page loaded successfully")
            self.status_label.setText("MITRE Attack Flow loaded successfully")
            self.status_label.setStyleSheet(styles.STATUS_LABEL_SUCCESS)
            self.log_to_console("Page loaded successfully")
            QTimer.singleShot(1000, self.inject_enhancement_script)
        else:
            self.logger.error("Page load failed")
            self.status_label.setText("Failed to load MITRE Attack Flow")
            self.status_label.setStyleSheet(styles.STATUS_LABEL_ERROR)
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
            self.status_label.setStyleSheet(styles.STATUS_LABEL_WARNING)
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
            file_path, _ = QFileDialog.getSaveFileName(
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
                self.status_label.setStyleSheet(styles.STATUS_LABEL_SUCCESS)
                self.log_to_console(f"Download started: {suggested_filename} -> {final_path}")
            else:
                download_item.cancel()
                self.log_to_console("Download cancelled by user")
        except Exception as e:
            self.logger.error(f"Error handling download: {e}")
            self.log_to_console(f"Download error: {str(e)}")
            try:
                download_item.cancel()
            except Exception:
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
            self.status_label.setStyleSheet(styles.STATUS_LABEL_SUCCESS)
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
        self.status_label.setStyleSheet(styles.STATUS_LABEL_SUCCESS)

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
                if open_in_system_browser():
                    QMessageBox.information(self, "Opened in Browser", "MITRE Attack Flow opened in your system browser.")
                    self.close()
                else:
                    QMessageBox.critical(self, "Browser Error", "Failed to open system browser.")
        except Exception as e:
            self.logger.error(f"Error in browser fallback offer: {e}")

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

# ---------------------------------------------------------------------------
# Section 3: Utils (mitre_flow_utils)
# ---------------------------------------------------------------------------

def setup_logging(platform_name):
    logger = logging.getLogger(f'mitre_flow_{platform_name}')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_file = os.path.join(os.path.dirname(__file__), '..', 'kanvas.log')
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

def detect_platform():
    system = platform.system()
    is_windows = system == "Windows"
    is_macos = system == "Darwin"
    is_linux = system == "Linux"
    platform_name = system.lower()
    if is_macos:
        machine = platform.machine()
        platform_name = "macos_arm64" if machine == "arm64" else "macos_intel"
    return platform_name, is_windows, is_macos, is_linux

def get_platform_info():
    platform_name, is_windows, is_macos, is_linux = detect_platform()
    info = {
        "platform_name": platform_name,
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": platform.architecture(),
        "is_windows": is_windows,
        "is_macos": is_macos,
        "is_linux": is_linux,
        "python_version": sys.version,
        "python_executable": sys.executable
    }
    try:
        from PySide6.QtCore import QT_VERSION_STR
        info["qt_version"] = QT_VERSION_STR
    except ImportError:
        info["qt_version"] = "Not available"
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        info["qtwebengine_available"] = True
    except ImportError:
        info["qtwebengine_available"] = False
    return info

def open_in_system_browser(url="https://center-for-threat-informed-defense.github.io/attack-flow/ui/"):
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to open system browser: {e}")
        return False

def show_platform_error_dialog(parent, error_type, technical_error=None):
    error_msg = get_platform_error_message(error_type)
    if technical_error:
        error_msg += f"\n\nTechnical error: {str(technical_error)}"
    reply = QMessageBox.question(
        parent,
        "QtWebEngine Not Available",
        error_msg + "\n\nWould you like to open MITRE Attack Flow in your system browser instead?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )
    if reply == QMessageBox.Yes:
        if open_in_system_browser():
            QMessageBox.information(parent, "Opened in Browser", "MITRE Attack Flow opened in your system browser.")
            return True
        QMessageBox.critical(parent, "Browser Error", "Failed to open system browser.")
        return False
    return False

def check_qtwebengine_availability():
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        from PySide6.QtWebEngineCore import QWebEngineProfile
        profile = QWebEngineProfile.defaultProfile()
        if not profile:
            return False, "QWebEngineProfile not available"
        return True, "QtWebEngine available and functional"
    except ImportError as e:
        return False, f"QtWebEngine import failed: {e}"
    except Exception as e:
        return False, f"QtWebEngine configuration error: {e}"

def validate_platform_dependencies():
    issues = check_platform_specific_issues()
    if issues:
        return False, "; ".join(issues)
    return True, "All platform dependencies satisfied"

def create_window_factory():
    class WindowFactory:
        @staticmethod
        def create_window(parent=None):
            platform_name, is_windows, is_macos, is_linux = detect_platform()
            config = get_platform_config()
            qtwebengine_ok, qtwebengine_msg = check_qtwebengine_availability()
            if not qtwebengine_ok:
                show_platform_error_dialog(parent, "import_error", qtwebengine_msg)
                return None
            deps_ok, deps_msg = validate_platform_dependencies()
            if not deps_ok:
                logging.getLogger(__name__).warning(f"Platform dependencies issue: {deps_msg}")
            window = MitreFlowWindowBase(parent, config)
            return window
    return WindowFactory

def get_enhancement_script(platform_name):
    return f"""
    (function() {{
        console.log('MITRE Attack Flow Enhancement Script Loaded ({platform_name})');
        function safeGet(obj, path, defaultValue) {{
            try {{
                return path.split('.').reduce((current, key) => {{
                    return (current && current[key] !== undefined) ? current[key] : defaultValue;
                }}, obj);
            }} catch (e) {{
                return defaultValue;
            }}
        }}
        if (window.File && window.FileReader && window.FileList && window.Blob) {{
            console.log('File API is available');
        }} else {{
            console.warn('File API is not fully supported');
        }}
        document.addEventListener('click', function(event) {{
            try {{
                const target = event.target;
                if (target && safeGet(target, 'textContent', '')) {{
                    const text = target.textContent.toLowerCase();
                    if (text.includes('save') || text.includes('export')) {{
                        console.log('Save/Export action detected:', text);
                        if (text.includes('save') && !text.includes('as image')) {{
                            console.log('Attempting to trigger save...');
                            const downloadLinks = document.querySelectorAll('a[download], button[data-action="download"]');
                            if (downloadLinks.length > 0) {{
                                console.log('Found download links:', downloadLinks.length);
                                downloadLinks[0].click();
                            }}
                        }}
                    }}
                }}
            }} catch (e) {{
                console.error('Error in click handler:', e.message);
            }}
        }});
        window.addEventListener('error', function(event) {{
            console.error('JavaScript Error:', safeGet(event, 'error.message', 'Unknown error'));
        }});
        setTimeout(function() {{
            try {{
                const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
                buttons.forEach(function(button) {{
                    try {{
                        if (safeGet(button, 'disabled', false)) {{
                            console.log('Found disabled button:', safeGet(button, 'textContent', safeGet(button, 'value', 'Unknown')));
                        }}
                    }} catch (e) {{
                        console.error('Error checking button:', e.message);
                    }}
                }});
                const menuItems = document.querySelectorAll('[role="menuitem"], .menu-item, .dropdown-item');
                console.log('Found menu items:', menuItems.length);
                menuItems.forEach(function(item) {{
                    try {{
                        console.log('Menu item:', safeGet(item, 'textContent', '').trim());
                    }} catch (e) {{
                        console.error('Error reading menu item:', e.message);
                    }}
                }});
            }} catch (e) {{
                console.error('Error in timeout handler:', e.message);
            }}
        }}, 2000);
    }})();
    """

def get_platform_logger():
    platform_name, _, _, _ = detect_platform()
    return setup_logging(platform_name)

# ---------------------------------------------------------------------------
# Section 4: Windows (mitre_flow_windows)
# ---------------------------------------------------------------------------

if platform.system() == "Windows":
    for key, value in PLATFORM_CONFIGS["windows"].get("environment", {}).items():
        os.environ[key] = value

def setup_windows_logging():
    logger = logging.getLogger('qt_win')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_file = os.path.join(os.path.dirname(__file__), '..', 'kanvas.log')
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

if platform.system() == "Windows":
    qt_win_logger = setup_windows_logging()
else:
    qt_win_logger = logging.getLogger("mitre_flow_windows")

class MitreFlowWindowWindows(MitreFlowWindowBase):
    def __init__(self, parent=None):
        config = get_platform_config()
        self.logger = qt_win_logger
        super().__init__(parent, config)
        self.logger.info("MitreFlowWindowWindows initialized")
        self.logger.debug(f"Parent window: {parent}")
        self.logger.debug(f"Environment: QTWEBENGINE_DISABLE_SANDBOX={os.environ.get('QTWEBENGINE_DISABLE_SANDBOX')}, QTWEBENGINE_CHROMIUM_FLAGS={os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS')}")

    def setup_platform_environment(self):
        super().setup_platform_environment()
        self.logger.debug("Windows-specific environment setup completed")
        issues = check_windows_issues()
        if issues:
            self.logger.warning(f"Windows-specific issues detected: {issues}")

    def handle_platform_specific_errors(self, error):
        error_str = str(error).lower()
        if "qtwebengine" in error_str:
            if "import" in error_str or "module" in error_str:
                return show_platform_error_dialog(self, "import_error", error)
            return show_platform_error_dialog(self, "runtime_error", error)
        return False

def check_windows_chrome_dependencies():
    qt_win_logger.debug("Starting Windows Chrome dependencies check")
    issues = []
    try:
        try:
            result = subprocess.run(['reg', 'query', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                issues.append("Visual C++ Redistributable 2015-2022 (x64) not found")
        except Exception:
            issues.append("Cannot check Visual C++ Redistributable status")
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), "QtWebEngineProcess.exe"),
            os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages", "PySide6", "QtWebEngineProcess.exe"),
            os.path.join(os.path.dirname(sys.executable), "Library", "bin", "QtWebEngineProcess.exe")
        ]
        qtwebengine_found = any(os.path.exists(p) for p in possible_paths)
        if not qtwebengine_found:
            issues.append("QtWebEngineProcess.exe not found in expected locations")
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
        chrome_found = any(os.path.exists(p) for p in chrome_paths)
        if not chrome_found:
            issues.append("No Chrome/Edge browser found - may affect QtWebEngine functionality")
        if issues:
            qt_win_logger.warning(f"Windows Chrome dependencies issues found: {issues}")
            return False, "; ".join(issues)
        qt_win_logger.info("All Windows Chrome dependencies found")
        return True, "All Windows Chrome dependencies found"
    except Exception as e:
        qt_win_logger.error(f"Error checking Windows dependencies: {e}")
        return False, f"Error checking Windows dependencies: {e}"

def open_mitre_flow_window_windows(parent=None):
    qt_win_logger.info("open_mitre_flow_window_windows called")
    qt_win_logger.debug(f"Parent window: {parent}")
    qt_win_logger.debug(f"Platform: {platform.system()} {platform.release()}")
    qt_win_logger.debug(f"Python version: {sys.version}")
    try:
        qt_win_logger.info("Checking QtWebEngine availability")
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
            from PySide6.QtWebEngineCore import QWebEngineProfile  # noqa: F401
            qt_win_logger.info("QtWebEngine imports successful")
        except ImportError as e:
            qt_win_logger.error(f"QtWebEngine import failed: {e}")
            error_msg = f"""
            QtWebEngine not available on Windows.

            Solutions:
            1. Install Visual C++ Redistributable 2015-2022 (x64)
            2. Use conda: conda install pyside6-qtwebengine
            3. Download pre-built wheels from PyPI
            4. Check Windows Defender exclusions

            Note: 32-bit Windows not supported. Windows Defender may block execution.

            Technical error: {str(e)}
            """
            reply = QMessageBox.question(
                parent,
                "QtWebEngine Not Available",
                error_msg + "\n\nWould you like to open MITRE Attack Flow in your system browser instead?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if open_in_system_browser():
                    QMessageBox.information(parent, "Opened in Browser", "MITRE Attack Flow opened in your system browser.")
                else:
                    QMessageBox.critical(parent, "Browser Error", "Failed to open system browser.")
            return None
        qt_win_logger.info("Checking Windows Chrome dependencies")
        chrome_ok, chrome_msg = check_windows_chrome_dependencies()
        if not chrome_ok:
            qt_win_logger.warning(f"Windows Chrome dependencies issue: {chrome_msg}")
            qt_win_logger.info("Proceeding anyway - QtWebEngine may still work")
        else:
            qt_win_logger.info("Windows Chrome dependencies check passed")
        qt_win_logger.info("Proceeding with QtWebEngine - will handle errors gracefully")
        qt_win_logger.info("Creating MitreFlowWindowWindows instance")
        window = MitreFlowWindowWindows(parent)
        qt_win_logger.info("Window created successfully")
        if parent:
            parent_geometry = parent.geometry()
            window_geometry = window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - window_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - window_geometry.height()) // 2
            window.move(x, y)
            qt_win_logger.debug(f"Window centered on parent at ({x}, {y})")
        qt_win_logger.info("MITRE Attack Flow window opened successfully")
        return window
    except Exception as e:
        qt_win_logger.error(f"Error opening MITRE Attack Flow window: {e}")
        qt_win_logger.error(f"Exception type: {type(e).__name__}")
        qt_win_logger.error(f"Exception args: {e.args}")
        try:
            reply = QMessageBox.question(
                parent,
                "MITRE Attack Flow Error",
                f"Failed to open MITRE Attack Flow window: {str(e)}\n\n"
                "Would you like to open MITRE Attack Flow in your system browser instead?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if open_in_system_browser():
                    QMessageBox.information(parent, "Opened in Browser", "MITRE Attack Flow opened in your system browser.")
                else:
                    QMessageBox.critical(parent, "Browser Error", "Failed to open system browser.")
        except Exception as fallback_error:
            qt_win_logger.error(f"Error in fallback: {fallback_error}")
            if parent:
                QMessageBox.critical(parent, "Error", f"Failed to open MITRE Attack Flow: {str(e)}")
        return None

# ---------------------------------------------------------------------------
# Section 5: Platform (mitre_flow_platform) - public API
# ---------------------------------------------------------------------------

class MitreFlowWindowMacos(MitreFlowWindowBase):
    def __init__(self, parent=None):
        config = get_platform_config()
        self.logger = get_platform_logger()
        super().__init__(parent, config)
        self.logger.info("MitreFlowWindowMacos initialized")

    def setup_platform_environment(self):
        super().setup_platform_environment()
        self.logger.debug("macOS-specific environment setup completed")
        if platform.machine() == "arm64":
            self.logger.info("Apple Silicon detected - compatibility mode enabled")
        issues = check_macos_issues()
        if issues:
            self.logger.warning(f"macOS-specific issues detected: {issues}")

    def handle_platform_specific_errors(self, error):
        error_str = str(error).lower()
        if "qtwebengine" in error_str:
            if "import" in error_str or "module" in error_str:
                return show_platform_error_dialog(self, "import_error", error)
            return show_platform_error_dialog(self, "runtime_error", error)
        return False

def open_mitre_flow_window_macos(parent=None):
    logger = get_platform_logger()
    logger.info("open_mitre_flow_window_macos called")
    try:
        qtwebengine_ok, qtwebengine_msg = check_qtwebengine_availability()
        if not qtwebengine_ok:
            return show_platform_error_dialog(parent, "import_error", qtwebengine_msg)
        window = MitreFlowWindowMacos(parent)
        if parent:
            parent_geometry = parent.geometry()
            window_geometry = window.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - window_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - window_geometry.height()) // 2
            window.move(x, y)
            logger.debug(f"Window centered on parent at ({x}, {y})")
        logger.info("MITRE Attack Flow window opened successfully")
        return window
    except Exception as e:
        logger.error(f"Error opening MITRE Attack Flow window: {e}")
        if hasattr(e, '__class__'):
            window_instance = MitreFlowWindowMacos()
            if window_instance.handle_platform_specific_errors(e):
                return None
        return show_platform_error_dialog(parent, "runtime_error", e)

def open_mitre_flow_window_linux(parent=None):
    logger = get_platform_logger()
    logger.info("open_mitre_flow_window_linux called - Linux not supported")
    try:
        message = "The MITRE Attack Flow feature is not supported on Linux systems.\n\nYou can access MITRE Attack Flow directly in your web browser at:\nhttps://center-for-threat-informed-defense.github.io/attack-flow/ui/\n\nWould you like to open this URL in your default browser?"
        reply = QMessageBox.question(
            parent,
            "MITRE Attack Flow - Linux Not Supported",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            try:
                webbrowser.open("https://center-for-threat-informed-defense.github.io/attack-flow/ui/")
                QMessageBox.information(parent, "Browser Opened", "MITRE Attack Flow opened in your default browser.")
                logger.info("MITRE Attack Flow opened in system browser")
            except Exception as browser_error:
                logger.error(f"Failed to open browser: {browser_error}")
                QMessageBox.critical(parent, "Browser Error", "Failed to open system browser. Please manually navigate to:\nhttps://center-for-threat-informed-defense.github.io/attack-flow/ui/")
        else:
            logger.info("User declined to open browser")
        return None
    except Exception as e:
        logger.error(f"Error in Linux MITRE Flow handler: {e}")
        QMessageBox.critical(parent, "Error", f"An error occurred: {str(e)}")
        return None

def _fallback_to_browser(parent, platform_name):
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Falling back to system browser for {platform_name}")
        return show_platform_error_dialog(parent, "import_error", f"Platform implementation not available for {platform_name}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in browser fallback: {e}")
        return None

def open_mitre_flow_window(parent=None):
    """Public API: open MITRE Attack Flow window (platform-specific)."""
    try:
        platform_name, is_windows, is_macos, is_linux = detect_platform()
        logger = logging.getLogger(__name__)
        logger.info(f"Detected platform: {platform_name}")
        platform_info = get_platform_info()
        logger.debug(f"Platform info: {platform_info}")
        if is_windows:
            logger.info("Loading Windows-specific MITRE Flow implementation")
            try:
                return open_mitre_flow_window_windows(parent)
            except ImportError as e:
                logger.error(f"Failed to import Windows MITRE Flow implementation: {e}")
                return _fallback_to_browser(parent, "Windows")
        if is_macos:
            logger.info("Loading macOS-specific MITRE Flow implementation")
            try:
                return open_mitre_flow_window_macos(parent)
            except Exception as e:
                logger.error(f"Failed to initialize macOS MITRE Flow implementation: {e}")
                return _fallback_to_browser(parent, "macOS")
        if is_linux:
            logger.info("Loading Linux-specific MITRE Flow implementation")
            try:
                return open_mitre_flow_window_linux(parent)
            except Exception as e:
                logger.error(f"Failed to initialize Linux MITRE Flow implementation: {e}")
                return _fallback_to_browser(parent, "Linux")
        logger.warning(f"Unknown platform detected: {platform_name}")
        return _fallback_to_browser(parent, platform_name)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in platform detection or window opening: {e}")
        return _fallback_to_browser(parent, "Unknown")
