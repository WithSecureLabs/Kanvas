import os
import sys
import logging
import platform
import webbrowser
from PySide6.QtWidgets import QMessageBox

def setup_logging(platform_name):
    logger = logging.getLogger(f'mitre_flow_{platform_name}')
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

def detect_platform():
    system = platform.system()
    is_windows = system == "Windows"
    is_macos = system == "Darwin"
    is_linux = system == "Linux"
    platform_name = system.lower()
    if is_macos:
        machine = platform.machine()
        if machine == "arm64":
            platform_name = "macos_arm64"
        else:
            platform_name = "macos_intel"
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
        from PySide6.QtWebEngineWidgets import QWebEngineView
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
    from .mitre_flow_config import get_platform_error_message
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
        else:
            QMessageBox.critical(parent, "Browser Error", "Failed to open system browser.")
            return False
    return False

def check_qtwebengine_availability():
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
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
    from .mitre_flow_config import check_platform_specific_issues
    issues = check_platform_specific_issues()
    if issues:
        return False, "; ".join(issues)
    else:
        return True, "All platform dependencies satisfied"

def create_window_factory():
    from .mitre_flow_core import MitreFlowWindowBase
    from .mitre_flow_config import get_platform_config
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

def setup_platform_environment():
    from .mitre_flow_config import setup_platform_environment as config_setup
    config_setup()

def get_platform_logger():
    platform_name, _, _, _ = detect_platform()
    return setup_logging(platform_name)