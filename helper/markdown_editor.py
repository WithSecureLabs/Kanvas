# code Reviewed 
import sys
import os
import re
import logging
import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextBrowser, QVBoxLayout, QWidget,
    QFileDialog, QPushButton, QTabWidget, QPlainTextEdit, QHBoxLayout,
    QMessageBox, QComboBox, QProgressDialog
)
from PySide6.QtGui import QFont, QAction, QKeySequence
from PySide6.QtCore import Qt, Slot

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

_editor_window_ref = None

def get_application_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    return application_path

class FormattedTextBrowser(QTextBrowser):
    def append_message(self, text, style="normal"):
        try:
            self.setReadOnly(False)
            if style == "normal":
                self.append(f"{text}")
            elif style == "highlight":
                self.append(f"<span style='color:#1976D2; font-weight:bold;'>{text}</span>")
            elif style == "system":
                self.append(f"<i style='color:#888888;'>{text}</i>")
            elif style == "error":
                self.append(f"<span style='color:#D32F2F; font-weight:bold;'>{text}</span>")
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            self.setReadOnly(True)
        except Exception as e:
            logger.error(f"Error displaying message: {str(e)}")
            self.append(f"<span style='color:#D32F2F;'>Error displaying message: {str(e)}</span>")
            self.setReadOnly(True)

class MarkdownViewerEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        global _editor_window_ref
        _editor_window_ref = self
        self.setWindowTitle("Markdown Viewer & Editor")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        base_width, base_height = 900, 700
        screen_geometry = QApplication.primaryScreen().geometry()
        x, y = (screen_geometry.width() - base_width) // 2, (screen_geometry.height() - base_height) // 2
        self.setGeometry(x, y, base_width, base_height)
        self.setStyleSheet("""
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
        """)
        self.current_file = None
        self.current_file_path = None
        self.modified = False
        self.setup_ui()
        self.setup_shortcuts()
        self.load_default_file()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet("background-color: #E0E0E0; border-bottom: 1px solid #CCCCCC;")
        main_layout.addWidget(toolbar_container)
        self.create_toolbar(toolbar_container)
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)
        self.create_view_tab()
        self.create_edit_tab()
        self.tab_widget.addTab(self.view_tab, "View")
        self.tab_widget.addTab(self.edit_tab, "Edit")
        self.tab_widget.currentChanged.connect(self.tab_changed)
        self.statusBar().showMessage("Ready", 3000)
        self.statusBar().setStyleSheet("QStatusBar { background-color: #F5F5F5; color: #424242; border-top: 1px solid #E0E0E0; }")
    
    def create_toolbar(self, container):
        logger.debug("Creating toolbar")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(15, 10, 15, 10)
        button_layout.setSpacing(10)
        self.file_dropdown = QComboBox()
        self.file_dropdown.setMinimumWidth(200)
        self.file_dropdown.setStyleSheet("""
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
        """)
        self.file_dropdown.addItem("Select a markdown file...")
        self.populate_markdown_files()
        self.file_dropdown.currentIndexChanged.connect(self.file_selected_from_dropdown)
        button_layout.addWidget(self.file_dropdown)
        button_layout.addStretch(1)
        button_style = """
            background-color: #444444; 
            color: white; 
            font-weight: normal;
            border-radius: 3px;
            padding: 5px 10px;
        """
        self.new_button = QPushButton("New")
        self.new_button.setMinimumWidth(80)
        self.new_button.setMaximumWidth(80)
        self.new_button.setMinimumHeight(30)
        self.new_button.setStyleSheet(button_style)
        self.new_button.clicked.connect(self.create_new_file)
        button_layout.addWidget(self.new_button)
        self.open_button = QPushButton("Open")
        self.open_button.setMinimumWidth(80)
        self.open_button.setMaximumWidth(80)
        self.open_button.setMinimumHeight(30)
        self.open_button.setStyleSheet(button_style)
        self.open_button.clicked.connect(self.open_file)
        button_layout.addWidget(self.open_button)
        self.save_button = QPushButton("Save")
        self.save_button.setMinimumWidth(80)
        self.save_button.setMaximumWidth(80)
        self.save_button.setMinimumHeight(30)
        self.save_button.setStyleSheet(button_style)
        self.save_button.clicked.connect(self.save_file)
        button_layout.addWidget(self.save_button)
        self.save_as_button = QPushButton("Save As")
        self.save_as_button.setMinimumWidth(80)
        self.save_as_button.setMaximumWidth(80)
        self.save_as_button.setMinimumHeight(30)
        self.save_as_button.setStyleSheet(button_style)
        self.save_as_button.clicked.connect(self.save_file_as)
        button_layout.addWidget(self.save_as_button)
        layout.addLayout(button_layout)

    def populate_markdown_files(self):
        try:
            application_dir = get_application_path()
            markdown_folder = os.path.join(application_dir, "markdown_files")
            if not os.path.exists(markdown_folder):
                os.makedirs(markdown_folder, exist_ok=True)
                self.statusBar().showMessage(f"Created markdown_files folder", 3000)
            while self.file_dropdown.count() > 1:
                self.file_dropdown.removeItem(1)
            try:
                files_in_folder = os.listdir(markdown_folder)
                markdown_files = [f for f in files_in_folder if f.lower().endswith('.md')]
                markdown_files.sort(key=str.lower)
            except OSError:
                markdown_files = []
                logger.warning("Could not list files in markdown_files folder")
            for filename in markdown_files:
                self.file_dropdown.addItem(filename)
            if markdown_files:
                self.statusBar().showMessage(f"Loaded {len(markdown_files)} markdown files", 3000)
            else:
                self.statusBar().showMessage("No markdown files found in markdown_files folder", 3000)
        except PermissionError:
            error_msg = "Permission denied accessing markdown_files folder"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg, 5000)
        except OSError as e:
            error_msg = f"File system error: {str(e)}"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg, 5000)
        except Exception as e:
            error_msg = f"Error loading markdown files: {str(e)}"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg, 3000)

    def file_selected_from_dropdown(self, index):
        if index > 0:
            selected_file = self.file_dropdown.currentText()
            application_dir = get_application_path()
            markdown_folder = os.path.join(application_dir, "markdown_files")
            file_path = os.path.join(markdown_folder, selected_file)
            if os.path.exists(file_path):
                self.load_markdown_file(file_path)
            else:
                logger.warning(f"Selected file does not exist: {file_path}")
    
    def create_view_tab(self):
        self.view_tab = QWidget()
        view_layout = QVBoxLayout(self.view_tab)
        view_layout.setContentsMargins(10, 10, 10, 10)
        self.text_browser = FormattedTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        view_font = QFont("Segoe UI", 10)
        self.text_browser.setFont(view_font)
        self.text_browser.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #222222;
                border: 1px solid #E0E0E0;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
        """)
        view_layout.addWidget(self.text_browser)
    
    def create_edit_tab(self):
        self.edit_tab = QWidget()
        edit_layout = QVBoxLayout(self.edit_tab)
        edit_layout.setContentsMargins(10, 10, 10, 10)
        self.text_edit = QPlainTextEdit()
        edit_font = QFont("Consolas", 11)
        self.text_edit.setFont(edit_font)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #FFFFFF;
                color: #222222;
                border: 1px solid #E0E0E0;
                padding: 10px;
                font-family: Monaco, Menlo, Consolas;
                font-size: 11pt;
            }
        """)
        self.text_edit.textChanged.connect(self.handle_text_changed)
        edit_layout.addWidget(self.text_edit)
        
    def setup_shortcuts(self):
        save_shortcut = QAction("Save", self)
        save_shortcut.setShortcut(QKeySequence.Save)
        save_shortcut.triggered.connect(self.save_file)
        self.addAction(save_shortcut)
        save_as_shortcut = QAction("Save As", self)
        save_as_shortcut.setShortcut(QKeySequence.SaveAs)
        save_as_shortcut.triggered.connect(self.save_file_as)
        self.addAction(save_as_shortcut)
        open_shortcut = QAction("Open", self)
        open_shortcut.setShortcut(QKeySequence.Open)
        open_shortcut.triggered.connect(self.open_file)
        self.addAction(open_shortcut)
    
    def load_default_file(self):
        folder_exists, markdown_folder = self.ensure_markdown_folder_exists()
        
        if folder_exists and markdown_folder:
            files = [f for f in os.listdir(markdown_folder) if f.lower().endswith('.md')]
            if files:
                default_file = os.path.join(markdown_folder, files[0])
                self.load_markdown_file(default_file)
                return
        application_dir = get_application_path()
        default_file = os.path.join(application_dir, "test.md")
        if os.path.exists(default_file):
            self.load_markdown_file(default_file)
        else:
            logger.info("No default file found")
    
    @Slot()
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            self.load_markdown_file(file_path)
    
    def load_markdown_file(self, file_path):
        try:
            self.current_file_path = file_path
            
            progress = QProgressDialog("Loading file...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Loading Markdown")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(200)
            progress.setValue(0)
            progress.show()
            progress.setValue(10)
            QApplication.processEvents()
            file_size = os.path.getsize(file_path)
            large_file = file_size > 100000
            logger.debug(f"File size: {file_size} bytes, large_file: {large_file}")
            with open(file_path, 'r', encoding='utf-8') as file:
                progress.setValue(30)
                QApplication.processEvents()
                markdown_text = file.read()
            progress.setValue(50)
            QApplication.processEvents()
            self.current_file = file_path
            self.modified = False
            self.text_edit.setPlainText(markdown_text)
            progress.setValue(70)
            progress.setLabelText("Rendering markdown...")
            QApplication.processEvents()
            html_content = self.markdown_to_html(markdown_text)
            progress.setValue(90)
            QApplication.processEvents()
            self.text_browser.setHtml(html_content)
            self.setWindowTitle(f"Markdown Viewer & Editor - {os.path.basename(file_path)}")
            self.statusBar().showMessage(f"Loaded {os.path.basename(file_path)}", 3000)
            self.update_dropdown_selection(file_path)
            
            progress.setValue(100)
        except FileNotFoundError:
            error_message = f"File not found: {file_path}"
            logger.error(error_message)
            self.text_browser.append_message(error_message, "error")
            QMessageBox.critical(self, "File Error", error_message)
        except PermissionError:
            error_message = f"Permission denied when accessing: {file_path}"
            logger.error(error_message)
            self.text_browser.append_message(error_message, "error")
            QMessageBox.critical(self, "Permission Error", error_message)
        except Exception as e:
            error_message = f"Error loading file: {str(e)}"
            logger.error(error_message)
            self.text_browser.append_message(error_message, "error")
            QMessageBox.critical(self, "Error", error_message)
    
    @Slot()
    def save_file(self):
        if self.current_file:
            try:
                progress = QProgressDialog("Saving file...", "Cancel", 0, 100, self)
                progress.setWindowTitle("Saving Markdown")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(200)
                progress.setValue(0)
                progress.show()
                progress.setValue(30)
                QApplication.processEvents()
                content = self.text_edit.toPlainText()
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(content)
                progress.setValue(70)
                QApplication.processEvents()
                self.statusBar().showMessage(f"Saved to {os.path.basename(self.current_file)}", 3000)
                self.modified = False
                self.setWindowTitle(f"Markdown Viewer & Editor - {os.path.basename(self.current_file)}")
                self._update_view()
                progress.setValue(100)
                return True
            except PermissionError:
                error_msg = "Permission denied when saving file."
                logger.error(error_msg)
                QMessageBox.critical(self, "Save Error", error_msg)
                return False
            except IOError as e:
                error_msg = f"I/O error when saving file: {str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Save Error", error_msg)
                return False
            except Exception as e:
                error_msg = f"Failed to save file: {str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Save Error", error_msg)
                return False
        else:
            logger.debug("No current file, calling save_file_as")
            return self.save_file_as()
    
    @Slot()
    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith('.md'):
                file_path += '.md'
            self.current_file = file_path
            if self.save_file():
                self.update_dropdown_with_file(file_path)
                return True
        return False
    
    def update_dropdown_selection(self, file_path):
        try:
            application_dir = get_application_path()
            markdown_folder = os.path.join(application_dir, "markdown_files")
            file_name = os.path.basename(file_path)
            
            if os.path.dirname(os.path.abspath(file_path)) == os.path.abspath(markdown_folder):
                for i in range(self.file_dropdown.count()):
                    if self.file_dropdown.itemText(i) == file_name:
                        self.file_dropdown.blockSignals(True)
                        self.file_dropdown.setCurrentIndex(i)
                        self.file_dropdown.blockSignals(False)
                        logger.debug(f"Updated dropdown selection to: {file_name}")
                        return
                self.file_dropdown.blockSignals(True)
                self.file_dropdown.addItem(file_name)
                self.file_dropdown.setCurrentIndex(self.file_dropdown.count() - 1)
                self.file_dropdown.blockSignals(False)
                logger.debug(f"Added and selected new file in dropdown: {file_name}")
            else:
                self.file_dropdown.blockSignals(True)
                self.file_dropdown.setCurrentIndex(0)  
                self.file_dropdown.blockSignals(False)
                logger.debug(f"File {file_name} is not in markdown_files folder, reset dropdown to default")
        except Exception as e:
            logger.error(f"Error updating dropdown selection: {str(e)}")

    def update_dropdown_with_file(self, file_path):
        application_dir = get_application_path()
        markdown_folder = os.path.join(application_dir, "markdown_files")
        file_name = os.path.basename(file_path)
        if os.path.dirname(os.path.abspath(file_path)) == os.path.abspath(markdown_folder):
            file_exists = False
            for i in range(self.file_dropdown.count()):
                if self.file_dropdown.itemText(i) == file_name:
                    file_exists = True
                    self.file_dropdown.setCurrentIndex(i)
                    break
            if not file_exists:
                self.file_dropdown.blockSignals(True)
                self.file_dropdown.addItem(file_name)
                self.file_dropdown.setCurrentIndex(self.file_dropdown.count() - 1)
                self.file_dropdown.blockSignals(False)
                logger.debug(f"Added new file to dropdown: {file_name}")
    
    @Slot()
    def create_new_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Create New Markdown File", "", "Markdown Files (*.md);;All Files (*)"
        )
        if file_path:
            if not file_path.lower().endswith('.md'):
                file_path += '.md'
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write("# New Document\n\nStart writing here...\n")
                self.load_markdown_file(file_path)
                self.update_dropdown_with_file(file_path)
                self.statusBar().showMessage(f"Created new file: {os.path.basename(file_path)}", 3000)
            except Exception as e:
                error_msg = f"Failed to create file: {str(e)}"
                logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
    
    @Slot()
    def handle_text_changed(self):
        if not self.modified:
            self.modified = True
            self.save_button.setEnabled(True)
            if self.current_file:
                self.setWindowTitle(f"Markdown Viewer & Editor - {os.path.basename(self.current_file)} *")
    
    @Slot(int)
    def tab_changed(self, index):
        if index == 0:
            self.update_view()
    
    def update_view(self):
        markdown_text = self.text_edit.toPlainText()
        if hasattr(self, 'current_file') and self.current_file:
            self.current_file_path = self.current_file
        html_content = self.markdown_to_html(markdown_text)
        self.text_browser.setHtml(html_content)
    
    def closeEvent(self, event):
        event.accept()
        
        global _editor_window_ref
        _editor_window_ref = None
    
    def get_language_specific_css(self):
        return """
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

    def markdown_to_html(self, markdown_text):
        try:
            logger.debug(f"Processing markdown text: {markdown_text[:200]}...")
            
            def convert_image_paths(text):
                def replace_markdown_img(match):
                    alt_text = match.group(1)
                    img_path = match.group(2)
                    
                    if img_path.startswith('./') or (not img_path.startswith('/') and not img_path.startswith('http')):
                        current_file = getattr(self, 'current_file_path', None)
                        if current_file:
                            base_dir = os.path.dirname(current_file)
                            abs_path = os.path.join(base_dir, img_path.lstrip('./'))
                            abs_path = os.path.abspath(abs_path)
                            return f'![{alt_text}](file://{abs_path})'
                    
                    return match.group(0)
                
                def replace_html_img(match):
                    full_match = match.group(0)
                    src_match = re.search(r'src=["\']([^"\']+)["\']', full_match)
                    if src_match:
                        img_path = src_match.group(1)
                        if img_path.startswith('./') or (not img_path.startswith('/') and not img_path.startswith('http')):
                            current_file = getattr(self, 'current_file_path', None)
                            if current_file:
                                base_dir = os.path.dirname(current_file)
                                abs_path = os.path.join(base_dir, img_path.lstrip('./'))
                                abs_path = os.path.abspath(abs_path)
                                return re.sub(r'src=["\'][^"\']+["\']', f'src="file://{abs_path}"', full_match)
                    return full_match
                
                text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_markdown_img, text)
                text = re.sub(r'<img[^>]+src=["\'][^"\']+["\'][^>]*>', replace_html_img, text)
                return text
            
            markdown_text = convert_image_paths(markdown_text)
            
            css = """
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
            """ + self.get_language_specific_css()
            html_content = markdown.markdown(
                markdown_text, 
                extensions=[
                    TableExtension(), 
                    FencedCodeExtension(),
                    'codehilite',
                    'nl2br',  
                ],
                extension_configs={
                    'codehilite': {
                        'css_class': 'highlight',
                        'use_pygments': True,
                        'linenums': False,
                        'guess_lang': True
                    }
                }
            )
            logger.debug("Successfully processed markdown with syntax highlighting")
            return f"<html><head>{css}</head><body>{html_content}</body></html>"
        except Exception as e:
            logger.error(f"Error rendering markdown: {str(e)}")
            try:
                html_content = markdown.markdown(
                    markdown_text, 
                    extensions=['nl2br']
                )
                return f"<html><head>{css}</head><body>{html_content}</body></html>"
            except Exception as fallback_error:
                logger.error(f"Fallback processing also failed: {str(fallback_error)}")
                return "<html><body><p>Error rendering markdown. Please check the file format.</p></body></html>"

    def ensure_markdown_folder_exists(self):
        try:
            application_dir = get_application_path()
            markdown_folder = os.path.join(application_dir, "markdown_files")
            if not os.path.exists(markdown_folder):
                os.makedirs(markdown_folder, exist_ok=True)
                return True, markdown_folder
            return True, markdown_folder
        except OSError as e:
            error_msg = f"Failed to create/access markdown_files folder: {str(e)}"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg, 5000)
            return False, None
        except Exception as e:
            error_msg = f"Unexpected error with markdown_files folder: {str(e)}"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg, 5000)
            return False, None

def handle_markdown_editor(parent=None):
    global _editor_window_ref
    if _editor_window_ref is not None and not _editor_window_ref.isHidden():
        _editor_window_ref.raise_()
        _editor_window_ref.activateWindow()
        return _editor_window_ref
    editor = MarkdownViewerEditor()
    editor.setAttribute(Qt.WA_DeleteOnClose, True)
    if parent:
        editor.setParent(parent, Qt.Window)
    editor.show()
    _editor_window_ref = editor
    return editor