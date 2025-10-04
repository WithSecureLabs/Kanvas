import platform
import subprocess
import os

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
        except:
            issues.append("Cannot check Visual C++ Redistributable status")
        possible_paths = [
            os.path.join(os.path.dirname(__import__('sys').executable), "QtWebEngineProcess.exe"),
            os.path.join(os.path.dirname(__import__('sys').executable), "Lib", "site-packages", "PySide6", "QtWebEngineProcess.exe"),
            os.path.join(os.path.dirname(__import__('sys').executable), "Library", "bin", "QtWebEngineProcess.exe")
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
        for package, description in package_checks:
            try:
                result = subprocess.run(['dpkg', '-l', package], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    issues.append(f"{package} ({description}) not found")
            except:
                break
        qtwebengine_paths = [
            "/usr/lib/x86_64-linux-gnu/qt6/libexec/QtWebEngineProcess",
            "/usr/lib/qt6/libexec/QtWebEngineProcess",
            "/usr/local/lib/qt6/libexec/QtWebEngineProcess"
        ]
        qtwebengine_found = False
        for path in qtwebengine_paths:
            if os.path.exists(path):
                qtwebengine_found = True
                break
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