# code reviewed 
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt
import requests
import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

def open_ransomware_kb_window(parent_window):
    kb_window = QWidget(parent_window.window)  # Use parent_window.window like Event ID window
    kb_window.setWindowTitle("Ransomware Victim Lookups")
    kb_window.resize(720, 600)  
    kb_window.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    main_layout = QVBoxLayout(kb_window)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(15, 15, 15, 15)
    
    input_layout = QHBoxLayout()
    input_label = QLabel("Victim Name:")
    input_label.setStyleSheet("font-size: 12pt;")
    input_layout.addWidget(input_label)
    
    victim_entry = QLineEdit()
    victim_entry.setPlaceholderText("Enter company or organization name")
    victim_entry.setStyleSheet("font-size: 10pt;")
    victim_entry.setMinimumWidth(300)
    input_layout.addWidget(victim_entry)
    
    search_button = QPushButton("Search")
    search_button.setFixedWidth(100)
    search_button.setStyleSheet("background-color: #4CAF50; color: white;")
    input_layout.addWidget(search_button)
    
    main_layout.addLayout(input_layout)
    results_label = QLabel("Results:")
    results_label.setStyleSheet("font-size: 12pt;")
    results_label.setContentsMargins(0, 10, 0, 5)
    main_layout.addWidget(results_label)
    result_text = QTextEdit()
    result_text.setStyleSheet("font-size: 10pt;")
    result_text.setReadOnly(True)  
    main_layout.addWidget(result_text, 1)
    
    button_layout = QHBoxLayout()
    close_button = QPushButton("Close")
    close_button.setFixedWidth(100)
    close_button.setStyleSheet("background-color: #d3d3d3; color: black;")
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)
    
    def search_victim():
        victim_user = victim_entry.text().strip()
        if not victim_user:
            QMessageBox.warning(kb_window, "Warning", "Please enter a victim name.")
            return
        result_text.clear()
        try:
            api_url = f"https://api.ransomware.live/v2/searchvictims/{victim_user}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    victims = [data]
                elif isinstance(data, list):
                    victims = data
                else:
                    logger.error("Unexpected data format received from ransomware API")
                    result_text.append("Unexpected data format received from the API.")
                    return
                if not victims:
                    logger.info(f"No victims found for search term: {victim_user}")
                    result_text.append("No victims found.")
                    return
                for victim in victims:
                    result_text.append(f"Victim: {victim.get('victim', 'Unknown')}")
                    result_text.append(f"Group: {victim.get('group', 'Unknown')}")
                    result_text.append(f"Country: {victim.get('country', 'Unknown')}")
                    result_text.append(f"Discovered: {victim.get('discovered', 'Unknown')}")
                    result_text.append(f"Domain: {victim.get('domain', 'Unknown')}")
                    result_text.append(f"Description: {victim.get('description', 'None')}")
                    result_text.append(f"Attack Date: {victim.get('attackdate', 'Unknown')}")
                    result_text.append(f"Claim URL: {victim.get('claim_url', 'None')}")
                    result_text.append(f"Screenshot: {victim.get('screenshot', 'None')}")
                    result_text.append(f"Activity: {victim.get('activity', 'None')}")
                    result_text.append(f"Infostealer: {victim.get('infostealer', 'None')}")
                    result_text.append(f"Duplicates: {victim.get('duplicates', 'None')}")
                    result_text.append(f"Extra Infos: {victim.get('extrainfos', 'None')}")
                    result_text.append(f"Press: {victim.get('press', 'None')}")
                    result_text.append("-" * 50)
            else:
                logger.error(f"API request failed with status code {response.status_code} for victim: {victim_user}")
                result_text.append(f"Error: API request failed with status code {response.status_code}.")
        except requests.exceptions.Timeout:
            logger.error(f"API request timeout for victim: {victim_user}")
            QMessageBox.critical(kb_window, "Error", "The request timed out. Please try again later.")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error during API request for victim: {victim_user}")
            QMessageBox.critical(kb_window, "Error", "Failed to connect to the API. Please check your internet connection.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception during API call for victim {victim_user}: {e}")
            QMessageBox.critical(kb_window, "Error", f"An error occurred: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during ransomware search for victim {victim_user}: {e}")
            QMessageBox.critical(kb_window, "Error", f"Unexpected error: {e}")
    search_button.clicked.connect(search_victim)
    close_button.clicked.connect(lambda: (logger.info("Closing Ransomware Knowledge Base window"), kb_window.close()))
    victim_entry.returnPressed.connect(search_victim)
    kb_window.show()
    return kb_window