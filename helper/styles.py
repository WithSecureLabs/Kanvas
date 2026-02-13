# Kanvas Application Styles
# Central place for all Qt widget styling used across the app: Qt stylesheet strings
# (CSS-like) and QColor constants. Covers main window, buttons, tabs, comboboxes,
# text editors, status bar, labels, tree views, knowledge-base windows,
# markdown editor, and shared color/theme values. Import from here to keep UI look
# consistent and to change themes in one place.
# Revised on 01/02/2026 by Jinto Antony

from PySide6.QtGui import QColor

# General Application Style
MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #f0f0f0;
    }
"""

# Color Constants
COLOR_HIGHLIGHT_BG = QColor(66, 139, 202, 50)
COLOR_IMPORTANT_BG = QColor(220, 53, 69, 50)
COLOR_MOUSE_OVER_BG = QColor(227, 242, 253, 100)
COLOR_ALTERNATE_ROW_BG = QColor(248, 249, 250, 100)
COLOR_IMPORTANT_TEXT = QColor(220, 53, 69)

# Button Styles
BUTTON_STYLE_BASE = """
    QPushButton {
        background-color: #4CAF50; 
        color: white; 
        padding: 8px;
        border-radius: 4px;
        border: none;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
    QPushButton:pressed {
        background-color: #3d8b40;
    }
"""

BUTTON_STYLE_SECONDARY = """
    QPushButton {
        background-color: #2196F3; 
        color: white; 
        padding: 8px;
        border-radius: 4px;
        border: none;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #0b7dda;
    }
    QPushButton:pressed {
        background-color: #0a6ebd;
    }
"""

BUTTON_STYLE_DANGER = """
    QPushButton {
        background-color: #f44336; 
        color: white; 
        padding: 8px;
        border-radius: 4px;
        border: none;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #da190b;
    }
    QPushButton:pressed {
        background-color: #c4170a;
    }
"""

BUTTON_STYLE_NEUTRAL = """
    QPushButton {
        background-color: #f0f0f0;
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 4px 8px;
        color: #333;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #e0e0e0;
        border-color: #999;
    }
    QPushButton:pressed {
        background-color: #d0d0d0;
    }
"""

BUTTON_STYLE_DARK = """
    background-color: #444444; 
    color: white; 
    font-weight: normal;
    border-radius: 3px;
    padding: 5px 10px;
"""

BUTTON_STYLE_PINK = """
    QPushButton {
        background-color: #FF69B4;
        color: white;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: normal;
    }
    QPushButton:hover {
        background-color: #FF1493;
    }
    QPushButton:pressed {
        background-color: #C71585;
    }
"""

BUTTON_STYLE_GREY = "background-color: #d3d3d3; color: black;"

# Tab Widget Styles
TAB_WIDGET_STYLE = """
    QTabWidget::pane {
        border: 1px solid #E0E0E0;
        background-color: #FAFAFA;
    }
    QTabBar::tab {
        background-color: #F5F5F5;
        color: #424242;
        padding: 10px 18px;
        border: 1px solid #E0E0E0;
        border-bottom: 0px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        min-width: 80px;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background-color: #555555;
        color: white;
    }
    QTabBar::tab:hover:!selected {
        background-color: #E0E0E0;
    }
"""

# ComboBox Styles
COMBOBOX_STYLE = """
    QComboBox {
        background-color: white;
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 4px 8px;
    }
    QComboBox:hover {
        border-color: #999;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #CCCCCC;
    }
"""

# Text Browser Styles
TEXT_BROWSER_STYLE = """
    QTextEdit {
        background-color: #FFFFFF;
        color: #222222;
        border: 1px solid #E0E0E0;
        padding: 10px;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
    }
"""

# Text Editor (plain text / code)
TEXT_EDITOR_STYLE = """
    QPlainTextEdit {
        background-color: #FFFFFF;
        color: #222222;
        border: 1px solid #E0E0E0;
        padding: 10px;
        font-family: Monaco, Menlo, Consolas;
        font-size: 11pt;
    }
"""

# Status Bar Style
STATUS_BAR_STYLE = """
    QStatusBar { 
        background-color: #F5F5F5; 
        color: #424242; 
        border-top: 1px solid #E0E0E0; 
    }
"""

# Label Styles
LABEL_TITLE_STYLE = "font-size: 18pt; font-weight: bold; color: #1a237e;"
LABEL_SUBTITLE_STYLE = "font-size: 16px; font-weight: bold; margin-bottom: 10px;"
LABEL_INFO_STYLE = "color: #666; font-size: 12px; margin-top: 10px;"
STATUS_BAR_TEXT_STYLE = "color: #808080; font-style: italic;"

# Toolbar Style
TOOLBAR_CONTAINER_STYLE = "background-color: #E0E0E0; border-bottom: 1px solid #CCCCCC;"

# Layout Styles
STYLE_MARGIN_HORIZONTAL = "margin-left: 10px; margin-right: 5px;"

# Dialog / Window
WINDOW_BG_WHITE = "background-color: white;"

# Mapping Attack / MITRE labels and widgets
LABEL_HEADER_BLUE = "color: #0066cc;"
LINE_DIVIDER = "background-color: #cccccc;"
LABEL_COUNT_RED = "color: #cc3333;"
LABEL_DESC_DARK = "color: #333333;"
LABEL_INFO_ITALIC = "color: #555555; font-style: italic;"
SCROLL_AREA_NO_BORDER = "border: none;"
CONTAINER_TRANSPARENT = "background-color: transparent;"
LABEL_MUTED_ITALIC = "color: #999999; font-style: italic;"
LABEL_EMPTY_MUTED = "color: #999999; font-style: italic; padding: 20px;"
LABEL_FOOTER = "color: #888888; font-style: italic;"

# Helper: returns QSS for tactic header with dynamic background color
def get_tactic_header_style(bg_color):
    return f"color: white; background-color: {bg_color}; padding: 3px 8px;"

# Inline button styles (short form for dialogs)
BUTTON_GREEN_INLINE = "background-color: #4CAF50; color: white;"
BUTTON_SAVE_COLUMNS = "background-color: #4CAF50; color: white; padding: 5px;"
BUTTON_GENERATE = "background-color: #4CAF50; color: white; padding: 8px 20px;"
BUTTON_UPDATE = "background-color: #4CAF50; color: white; padding: 6px 20px;"
BUTTON_PADDING_ONLY = "padding: 6px 20px;"
BUTTON_SHOW_PADDING = "padding: 4px 8px;"
BUTTON_SEARCH_COMPACT = "background-color: #2196F3; color: white; padding: 4px 12px;"
BUTTON_CLEAR_MINIMAL = "padding: 4px 12px;"

# Report Builder
LABEL_INFO_ITALIC_10PT = "color: #666; font-style: italic; font-size: 10pt;"
LABEL_BOLD = "font-weight: bold;"

# Mapping Defend
LABEL_TECH_TITLE_BLUE = "color: #0077b6;"
LABEL_NO_TECH = "color: #555; padding-left: 30px;"
LABEL_DROPDOWN = "color: #333; margin-top: 10px;"
LABEL_NO_RESULTS = "color: #d32f2f; font-weight: bold;"
LABEL_ERROR_RED = "color: red;"
BUTTON_COPY_TEAL = """
    QPushButton {
        background-color: #00c4b4;
        color: white;
        font-weight: bold;
        border: none;
        padding: 6px 16px;
    }
"""
BUTTON_D3FEND_BLUE = """
    QPushButton {
        background-color: #0077b6;
        color: white;
        font-weight: bold;
        border: none;
        padding: 6px 16px;
    }
"""

# MITRE Flow Core
LABEL_TITLE_DARK = "color: #2c3e50; margin: 5px;"
BUTTON_STYLE_REFRESH = """
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #21618c;
    }
"""
BUTTON_STYLE_CLOSE_RED = """
    QPushButton {
        background-color: #e74c3c;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #c0392b;
    }
    QPushButton:pressed {
        background-color: #a93226;
    }
"""
WEB_ENGINE_VIEW_STYLE = """
    QWebEngineView {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
    }
"""
CONSOLE_LABEL_STYLE = "color: #7f8c8d; font-weight: bold; margin-bottom: 5px;"
CONSOLE_TEXT_EDIT_STYLE = """
    QTextEdit {
        background-color: #2c3e50;
        color: #ecf0f1;
        border: 1px solid #34495e;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 10pt;
    }
"""
STATUS_LABEL_DEFAULT = "color: #7f8c8d; font-style: italic; margin: 5px;"
STATUS_LABEL_ERROR = "color: #e74c3c; font-style: italic; margin: 5px;"
STATUS_LABEL_WARNING = "color: #f39c12; font-style: italic; margin: 5px;"
STATUS_LABEL_SUCCESS = "color: #27ae60; font-style: italic; margin: 5px;"

# Lookups
LABEL_FONT_12PT = "font-size: 12pt;"
LABEL_FONT_10PT = "font-size: 10pt;"
HEADER_HIGHLIGHT_BG = "#FFA500"
HEADER_HIGHLIGHT_FG = "white"
KEYWORD_HIGHLIGHT_BG = "#FF0000"
KEYWORD_HIGHLIGHT_FG = "white"
SUCCESS_HIGHLIGHT_BG = "#00AA00"
SUCCESS_HIGHLIGHT_FG = "white"
HTML_DANGER_COLOR = "#dc3545"
HTML_SUCCESS_COLOR = "#28a745"

# System type / inputs
INPUT_LINE_STYLE = "padding: 8px; font-size: 11pt; border: 1px solid #ccc; border-radius: 4px;"

# Knowledge Base (KB) resources - shared text/tree/detail styles
TEXT_EDIT_KB_DETAIL_DIALOG = """
    QTextEdit {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 15px;
        font-family: 'Consolas', 'Courier New', 'Monaco', 'Menlo', 'DejaVu Sans Mono', 'Liberation Mono', monospace;
        font-size: 10pt;
        line-height: 1.5;
        color: #24292e;
    }
"""
TEXT_EDIT_KB_LIST_LIGHT = """
    QTextEdit {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        font-family: 'Courier New', monospace;
        font-size: 10pt;
    }
"""
TREE_VIEW_KB_STYLE = """
    QTreeView {
        background-color: #ffffff;
        alternate-background-color: #f8f9fa;
        selection-background-color: #007acc;
        selection-color: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        gridline-color: #e9ecef;
        font-size: 10pt;
    }
    QTreeView::item {
        padding: 6px 10px;
        border-bottom: 1px solid #f1f3f4;
    }
    QTreeView::item:hover {
        background-color: #e3f2fd;
    }
    QTreeView::item:selected {
        background-color: #007acc;
        color: white;
    }
    QHeaderView::section {
        background-color: #f8f9fa;
        color: #495057;
        padding: 10px 12px;
        border: none;
        border-bottom: 2px solid #dee2e6;
        border-right: 1px solid #e9ecef;
        font-weight: bold;
        font-size: 10pt;
    }
    QHeaderView::section:hover {
        background-color: #e9ecef;
    }
"""
DETAIL_VIEW_KB_STYLE = """
    QTextEdit {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 15px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 10pt;
        line-height: 1.5;
        color: #24292e;
    }
"""
FONT_KB_MONOSPACE = "Consolas, Courier New, Monaco, Menlo, DejaVu Sans Mono, Liberation Mono, monospace"

# Event ID / resources_data tree (distinct style with gradient)
TREE_VIEW_EVENT_ID_STYLE = """
    QTreeView {
        background-color: #ffffff;
        alternate-background-color: #fafbfc;
        selection-background-color: #0078d4;
        selection-color: white;
        border: 1px solid #d1d5da;
        border-radius: 6px;
        gridline-color: #e1e4e8;
        font-size: 11pt;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QTreeView::item {
        padding: 8px 12px;
        border-bottom: 1px solid #f1f3f4;
        min-height: 20px;
    }
    QTreeView::item:hover {
        background-color: #f1f8ff;
        border-left: 3px solid #0078d4;
    }
    QTreeView::item:selected {
        background-color: #0078d4;
        color: white;
        border-left: 3px solid #106ebe;
    }
    QHeaderView::section {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #f6f8fa, stop:1 #e1e4e8);
        color: #24292e;
        padding: 12px 15px;
        border: none;
        border-bottom: 2px solid #d1d5da;
        border-right: 1px solid #e1e4e8;
        font-weight: 600;
        font-size: 11pt;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QHeaderView::section:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #e1e4e8, stop:1 #d1d5da);
    }
    QHeaderView::section:first {
        border-top-left-radius: 6px;
    }
    QHeaderView::section:last {
        border-top-right-radius: 6px;
    }
"""

# TreeView Styles
TREE_VIEW_MODERN_STYLE_TEMPLATE = """
        QTreeView {{
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            selection-background-color: #007acc;
            selection-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            outline: none;
            gridline-color: #e9ecef;
            {}
        }}

        QTreeView::item {{
            padding: 8px 12px;
            border-bottom: 1px solid #f1f3f4;
            min-height: 24px;
        }}

        QTreeView::item:hover {{
            background-color: #e3f2fd;
            color: #1976d2;
        }}

        QTreeView::item:selected {{
            background-color: #007acc;
            color: white;
        }}

        QTreeView::item:selected:hover {{
            background-color: #005a9e;
        }}

        QTreeView::branch {{
            background: transparent;
        }}

        QTreeView::branch:has-children:!has-siblings:closed,
        QTreeView::branch:closed:has-children:has-siblings {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #666666;
            width: 0px;
            height: 0px;
        }}

        QTreeView::branch:open:has-children:!has-siblings,
        QTreeView::branch:open:has-children:has-siblings {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-bottom: 5px solid #666666;
            width: 0px;
            height: 0px;
        }}

        QHeaderView::section {{
            background-color: #f8f9fa;
            color: #495057;
            padding: 12px 16px;
            border: none;
            border-bottom: 2px solid #dee2e6;
            border-right: 1px solid #e9ecef;
            font-weight: bold;
            font-size: 10pt;
        }}

        QHeaderView::section:hover {{
            background-color: #e9ecef;
        }}

        QHeaderView::section:pressed {{
            background-color: #dee2e6;
        }}

        QScrollBar:vertical {{
            background-color: #f8f9fa;
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: #cbd5e0;
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: #a0aec0;
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: #f8f9fa;
            height: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: #cbd5e0;
            border-radius: 6px;
            min-width: 20px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: #a0aec0;
        }}

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
"""

TREE_VIEW_STANDARD_STYLE_TEMPLATE = """
        QTreeView {{
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            selection-background-color: #007acc;
            selection-color: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            gridline-color: #e9ecef;
            {}
        }}
        QTreeView::item {{
            padding: 6px 10px;
            border-bottom: 1px solid #f1f3f4;
            min-height: 22px;
        }}
        QTreeView::item:hover {{
            background-color: #e3f2fd;
            color: #1976d2;
        }}
        QTreeView::item:selected {{
            background-color: #007acc;
            color: white;
        }}
        QTreeView::item:selected:hover {{
            background-color: #005a9e;
        }}
        QHeaderView::section {{
            background-color: #f8f9fa;
            color: #495057;
            padding: 10px 12px;
            border: none;
            border-bottom: 2px solid #dee2e6;
            border-right: 1px solid #e9ecef;
            font-weight: bold;
            font-size: 9pt;
        }}
        QHeaderView::section:hover {{
            background-color: #e9ecef;
        }}
        QHeaderView::section:pressed {{
            background-color: #dee2e6;
        }}
        QScrollBar:vertical {{
            background-color: #f8f9fa;
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background-color: #cbd5e0;
            border-radius: 5px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: #a0aec0;
        }}
"""

# Markdown Editor Styles
MARKDOWN_EDITOR_GLOBAL_STYLE = """
    QMainWindow {
        background-color: #ffffff;
    }
    QPushButton {
        background-color: #444444;
        color: #FFFFFF;
        font-weight: bold;
        border: none;
        border-radius: 4px;
        padding: 10px 15px;
        min-width: 120px;
        margin: 2px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #666666;
    }
    QPushButton:pressed {
        background-color: #222222;
    }
    QPushButton:disabled {
        background-color: #888888;
        color: #DDDDDD;
    }
""" + TAB_WIDGET_STYLE

MARKDOWN_COMBOBOX_STYLE = """
    QComboBox {
        background-color: white;
        color: #333333;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 5px;
        font-size: 11px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #CCCCCC;
    }
"""

MARKDOWN_SYNTAX_HIGHLIGHT_CSS = """
    .highlight .k { color: #d73a49 !important; font-weight: bold; }
    .highlight .s { color: #032f62 !important; }
    .highlight .c { color: #6a737d !important; font-style: italic; }
    .highlight .n { color: #24292e !important; }
    .highlight .o { color: #d73a49 !important; }
    .highlight .p { color: #24292e !important; }
    .highlight .nb { color: #005cc5 !important; }
    .highlight .mi { color: #005cc5 !important; }
    .highlight .mf { color: #005cc5 !important; }
    .highlight .mh { color: #005cc5 !important; }
    .highlight .mo { color: #005cc5 !important; }
    .highlight .sa { color: #032f62 !important; }
    .highlight .sb { color: #032f62 !important; }
    .highlight .sc { color: #032f62 !important; }
    .highlight .dl { color: #032f62 !important; }
    .highlight .sd { color: #032f62 !important; }
    .highlight .s2 { color: #032f62 !important; }
    .highlight .se { color: #032f62 !important; }
    .highlight .sh { color: #032f62 !important; }
    .highlight .si { color: #032f62 !important; }
    .highlight .sx { color: #032f62 !important; }
    .highlight .sr { color: #032f62 !important; }
    .highlight .s1 { color: #032f62 !important; }
    .highlight .ss { color: #032f62 !important; }
    .highlight .bp { color: #24292e !important; }
    .highlight .fm { color: #6f42c1 !important; font-weight: bold; }
    .highlight .vc { color: #005cc5 !important; }
    .highlight .vg { color: #005cc5 !important; }
    .highlight .vi { color: #005cc5 !important; }
    .highlight .vm { color: #005cc5 !important; }
    .highlight .il { color: #005cc5 !important; }
    .highlight .err { color: #d73a49 !important; background-color: #f8f9fa !important; }
    .highlight .w { color: #6a737d !important; background-color: #f8f9fa !important; }
    .highlight .l { color: #24292e !important; }
    .highlight .ld { color: #24292e !important; }
    .highlight .nf { color: #6f42c1 !important; font-weight: bold; }
    .highlight .nc { color: #005cc5 !important; font-weight: bold; }
    .highlight .na { color: #005cc5 !important; }
    .highlight .nt { color: #d73a49 !important; }
    .highlight .c1 { color: #6a737d !important; font-style: italic; }
    .highlight .cm { color: #6a737d !important; font-style: italic; }
    .highlight pre {
        color: #212529 !important;
        background-color: #f8f9fa !important;
    }
    .highlight pre code {
        color: #212529 !important;
        background-color: transparent !important;
    }
    pre code {
        color: #212529 !important;
        background-color: transparent !important;
    }
    .highlight pre code:not([class]) {
        color: #212529 !important;
    }
    .highlight pre code {
        color: #212529 !important;
    }
    .highlight {
        position: relative;
    }
    .highlight .nf { color: #dcdcaa !important; font-weight: bold; }
    .highlight .nc { color: #4ec9b0 !important; font-weight: bold; }
    .highlight .na { color: #4ec9b0 !important; }
    .highlight .nt { color: #569cd6 !important; }
    .highlight .c1 { color: #6a9955 !important; font-style: italic; }
    .highlight .cm { color: #6a9955 !important; font-style: italic; }
    pre, .highlight {
        background-color: #f8f9fa !important;
        color: #212529 !important;
    }
    pre *, .highlight * {
        color: inherit !important;
    }
"""

MARKDOWN_HTML_CSS_TEMPLATE = """
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.4;
            padding: 20px;
            max-width: 900px;
            margin: 0;
            color: #333;
            font-weight: normal;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #444;
            margin-top: 20px;
            margin-bottom: 10px;
            font-weight: 600;
        }
        h1 { font-size: 1.8em; padding-bottom: 0.2em; }
        h2 { font-size: 1.4em; padding-bottom: 0.2em; }
        h3 { font-size: 1.2em; }
        h4 { font-size: 1.1em; }
        p { margin: 10px 0; }
        a { color: #0366d6; text-decoration: none; }
        pre {
            background-color: #f8f9fa !important;
            color: #212529 !important;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.5;
            border: 1px solid #dee2e6;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        code {
            background-color: #f1f1f1;
            color: #d63384;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
            font-size: 0.9em;
            border: 1px solid #e1e1e1;
        }
        pre code {
            background-color: transparent !important;
            color: #212529 !important;
            padding: 0;
            border: none;
            font-size: inherit;
        }
        .highlight {
            background-color: #f8f9fa !important;
            border-radius: 8px;
            overflow: hidden;
            margin: 20px 0;
            border: 1px solid #dee2e6;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .highlight pre {
            margin: 0;
            border: none;
            border-radius: 0;
            background-color: #f8f9fa !important;
            color: #212529 !important;
        }
        .highlight .code {
            padding: 20px;
            background-color: #f8f9fa !important;
        }
        .highlight .highlight {
            background-color: #f8f9fa !important;
        }
        .highlight .highlight pre {
            background-color: #f8f9fa !important;
            color: #212529 !important;
        }
        blockquote {
            padding: 0 1em;
            color: #555;
            border-left: 0.25em solid #dfe2e5;
            margin: 0.5em 0;
        }
        ul, ol { padding-left: 2em; margin: 10px 0; }
        li { margin: 5px 0; }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        table th {
            background-color: #f2f2f2;
            font-weight: bold;
            text-align: left;
        }
        table th, table td {
            border: 1px solid #ddd;
            padding: 8px 12px;
        }
        hr { height: 1px; background-color: #e1e4e8; border: 0; margin: 20px 0; }
    </style>
"""
