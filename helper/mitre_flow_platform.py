import platform
import logging
import webbrowser
from PySide6.QtWidgets import QMessageBox
from .mitre_flow_utils import detect_platform, get_platform_info, open_in_system_browser, show_platform_error_dialog, get_platform_logger, check_qtwebengine_availability
from .mitre_flow_core import MitreFlowWindowBase

class MitreFlowWindowMacos(MitreFlowWindowBase):
    def __init__(self, parent=None):
        from .mitre_flow_config import get_platform_config
        config = get_platform_config()
        self.logger = get_platform_logger()
        super().__init__(parent, config)
        self.logger.info("MitreFlowWindowMacos initialized")
    
    def setup_platform_environment(self):
        super().setup_platform_environment()
        self.logger.debug("macOS-specific environment setup completed")
        if platform.machine() == "arm64":
            self.logger.info("Apple Silicon detected - compatibility mode enabled")
        from .mitre_flow_config import check_macos_issues
        issues = check_macos_issues()
        if issues:
            self.logger.warning(f"macOS-specific issues detected: {issues}")
    
    def handle_platform_specific_errors(self, error):
        error_str = str(error).lower()
        if "qtwebengine" in error_str:
            if "import" in error_str or "module" in error_str:
                return show_platform_error_dialog(self, "import_error", error)
            else:
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

def open_mitre_flow_window(parent=None):
    try:
        platform_name, is_windows, is_macos, is_linux = detect_platform()
        logger = logging.getLogger(__name__)
        logger.info(f"Detected platform: {platform_name}")
        platform_info = get_platform_info()
        logger.debug(f"Platform info: {platform_info}")
        if is_windows:
            logger.info("Loading Windows-specific MITRE Flow implementation")
            try:
                from .mitre_flow_windows import open_mitre_flow_window_windows
                return open_mitre_flow_window_windows(parent)
            except ImportError as e:
                logger.error(f"Failed to import Windows MITRE Flow implementation: {e}")
                return _fallback_to_browser(parent, "Windows")
        elif is_macos:
            logger.info("Loading macOS-specific MITRE Flow implementation")
            try:
                return open_mitre_flow_window_macos(parent)
            except Exception as e:
                logger.error(f"Failed to initialize macOS MITRE Flow implementation: {e}")
                return _fallback_to_browser(parent, "macOS")
        elif is_linux:
            logger.info("Loading Linux-specific MITRE Flow implementation")
            try:
                return open_mitre_flow_window_linux(parent)
            except Exception as e:
                logger.error(f"Failed to initialize Linux MITRE Flow implementation: {e}")
                return _fallback_to_browser(parent, "Linux")
        else:
            logger.warning(f"Unknown platform detected: {platform_name}")
            return _fallback_to_browser(parent, platform_name)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in platform detection or window opening: {e}")
        return _fallback_to_browser(parent, "Unknown")

def _fallback_to_browser(parent, platform_name):
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Falling back to system browser for {platform_name}")
        return show_platform_error_dialog(parent, "import_error", f"Platform implementation not available for {platform_name}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in browser fallback: {e}")
        return None
