import os
import sys
import logging
import platform
import webbrowser
import subprocess
from datetime import datetime
from PySide6.QtWidgets import QMessageBox
from .mitre_flow_core import MitreFlowWindowBase
from .mitre_flow_utils import get_platform_logger, show_platform_error_dialog, check_qtwebengine_availability

def setup_windows_logging():
    logger = logging.getLogger('qt_win')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_file = os.path.join(os.path.dirname(__file__), '..', 'kanvas.log')
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

qt_win_logger = setup_windows_logging()

class MitreFlowWindowWindows(MitreFlowWindowBase):
    def __init__(self, parent=None):
        from .mitre_flow_config import get_platform_config
        config = get_platform_config()
        self.logger = qt_win_logger  
        super().__init__(parent, config)
        self.logger.info("MitreFlowWindowWindows initialized")
        self.logger.debug(f"Parent window: {parent}")
        self.logger.debug(f"Environment variables set: QTWEBENGINE_DISABLE_SANDBOX={os.environ.get('QTWEBENGINE_DISABLE_SANDBOX')}, QTWEBENGINE_CHROMIUM_FLAGS={os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS')}")
    
    def setup_platform_environment(self):
        super().setup_platform_environment()
        self.logger.debug("Windows-specific environment setup completed")
        from .mitre_flow_config import check_windows_issues
        issues = check_windows_issues()
        if issues:
            self.logger.warning(f"Windows-specific issues detected: {issues}")
    
    def handle_platform_specific_errors(self, error):
        error_str = str(error).lower()
        if "qtwebengine" in error_str:
            if "import" in error_str or "module" in error_str:
                return show_platform_error_dialog(self, "import_error", error)
            else:
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
        except:
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
        if issues:
            qt_win_logger.warning(f"Windows Chrome dependencies issues found: {issues}")
            return False, "; ".join(issues)
        else:
            qt_win_logger.info("All Windows Chrome dependencies found")
            return True, "All Windows Chrome dependencies found"
    except Exception as e:
        qt_win_logger.error(f"Error checking Windows dependencies: {e}")
        return False, f"Error checking Windows dependencies: {e}"

def open_in_system_browser(url="https://center-for-threat-informed-defense.github.io/attack-flow/ui/"):
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to open system browser: {e}")
        return False

def open_mitre_flow_window_windows(parent=None):
    qt_win_logger.info("open_mitre_flow_window_windows called")
    qt_win_logger.debug(f"Parent window: {parent}")
    qt_win_logger.debug(f"Platform: {platform.system()} {platform.release()}")
    qt_win_logger.debug(f"Python version: {sys.version}")
    try:
        qt_win_logger.info("Checking QtWebEngine availability")
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtWebEngineCore import QWebEngineProfile
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
