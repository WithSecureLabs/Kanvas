# code reviewed 
import sqlite3
import os
import logging
import numpy as np
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

class SystemTypeManager:
    def __init__(self, db_path: str, images_dir: str = "images"):
        self.db_path = db_path
        self.images_dir = images_dir
        self.system_types = {}
        self.cache_ttl = 3600
        self.last_cache_update = 0
        self.logger = logging.getLogger(__name__)
        self.populate_default_system_types()
        self.load_system_types()
    
    def populate_default_system_types(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM system_types")
            count = cursor.fetchone()[0]
            if count == 0:
                default_types = [
                    ('Attacker-Machine', 'Attacker Machine', 'Attacker', 'attacker_logo.png', '#ff0000', 'Malicious systems', 1),
                    ('Server-DC', 'Domain Controller', 'Server', 'dc.png', '#9932cc', 'Active Directory Domain Controllers', 2),
                    ('Server-Database', 'Database Server', 'Server', 'database_icon.png', '#2ecc71', 'Database management systems', 3),
                    ('Server-Web', 'Web Server', 'Server', 'webserver_icon.png', '#e67e22', 'Web application servers', 4),
                    ('Server-Application', 'Application Server', 'Server', 'appserver_icon.png', '#8e44ad', 'Business application servers', 5),
                    ('Server-File', 'File Server', 'Server', 'fileserver_icon.png', '#34495e', 'File storage servers', 6),
                    ('Server-Generic', 'Generic Server', 'Server', 'server_icon.png', '#e74c3c', 'Generic server systems', 7),
                    ('Server-Terminal SRV', 'Terminal Server', 'Server', 'server_icon.png', '#e74c3c', 'Terminal services servers', 8),
                    ('Gateway-Firewall', 'Firewall', 'Gateway', 'firewall_icon.png', '#ff8c00', 'Network security devices', 9),
                    ('Gateway-VPN', 'VPN Gateway', 'Gateway', 'vpn_logo.png', '#4169e1', 'Virtual Private Network gateways', 10),
                    ('Gateway-Switch', 'Network Switch', 'Gateway', 'switch_icon.png', '#00bfff', 'Network switching devices', 11),
                    ('Gateway-Router', 'Router', 'Gateway', 'router_icon.png', '#ff6347', 'Network routing devices', 12),
                    ('Gateway-Web-Proxy', 'Web Proxy', 'Gateway', 'proxy_icon.png', '#8a2be2', 'Web proxy servers', 13),
                    ('Gateway-Email', 'Email Server', 'Gateway', 'email_icon.png', '#ff69b4', 'Email messaging servers', 14),
                    ('Gateway-DNS', 'DNS Server', 'Gateway', 'dns_icon.png', '#1e90ff', 'Domain Name System servers', 15),
                    ('Gateway-Generic', 'Generic Gateway', 'Gateway', 'router_icon.png', '#ff6347', 'Generic gateway devices', 16),
                    ('Desktop', 'Desktop Computer', 'Client', 'computer_icon.png', '#3498db', 'Desktop workstations', 17),
                    ('Mobile', 'Mobile Device', 'Client', 'mobile_icon.png', '#00ff7f', 'Mobile phones and tablets', 18),
                    ('OT-Device', 'OT Device', 'OT', 'ot_icon.png', '#ff8c42', 'Operational Technology devices', 19),
                    ('UnKnown', 'Unknown System', 'Unknown', 'unknown.png', '#808080', 'Unknown or unidentified systems', 20)
                ]
                cursor.executemany("""
                    INSERT INTO system_types (name, display_name, category, icon_filename, fallback_color, description, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, default_types)
                conn.commit()
                self.logger.info(f"Populated {len(default_types)} default system types")
        except sqlite3.Error as e:
            self.logger.error(f"Error populating default system types: {e}")
        finally:
            if conn:
                conn.close()
    
    def load_system_types(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, display_name, category, icon_filename, fallback_color, 
                       description, is_active, sort_order
                FROM system_types 
                WHERE is_active = 1 
                ORDER BY sort_order, display_name
            """)
            self.system_types = {}
            for row in cursor.fetchall():
                system_type = {
                    'id': row[0],
                    'name': row[1],
                    'display_name': row[2],
                    'category': row[3],
                    'icon_filename': row[4],
                    'fallback_color': row[5],
                    'description': row[6],
                    'is_active': bool(row[7]),
                    'sort_order': row[8]
                }
                self.system_types[row[1]] = system_type
            self.last_cache_update = datetime.now().timestamp()
            self.logger.info(f"Loaded {len(self.system_types)} system types from database")
        except sqlite3.Error as e:
            self.logger.error(f"Error loading system types: {e}")
            self.load_fallback_system_types()
        finally:
            if conn:
                conn.close()
    
    def load_fallback_system_types(self):
        fallback_types = [
            'Attacker-Machine', 'Server-Generic', 'Server-Application', 'Server-Web',
            'Server-DC', 'Server-Terminal SRV', 'Server-Database', 'Gateway-Generic',
            'Gateway-Firewall', 'Gateway-VPN', 'Gateway-Router', 'Gateway-Switch',
            'Gateway-Email', 'Gateway-Web Proxy', 'Gateway-DNS', 'Desktop', 'Mobile',
            'OT Device', 'UnKnown'
        ]
        self.system_types = {}
        for i, name in enumerate(fallback_types):
            self.system_types[name] = {
                'id': i + 1,
                'name': name,
                'display_name': name.replace('-', ' '),
                'category': self.guess_category(name),
                'icon_filename': None,
                'fallback_color': '#808080',
                'description': f'System type: {name}',
                'is_active': True,
                'sort_order': i + 1
            }
        self.logger.warning("Using fallback system types due to database error")
    
    def guess_category(self, name: str) -> str:
        name_lower = name.lower()
        if 'attacker' in name_lower:
            return 'Attacker'
        elif 'server' in name_lower:
            return 'Server'
        elif 'gateway' in name_lower:
            return 'Gateway'
        elif 'desktop' in name_lower or 'mobile' in name_lower:
            return 'Client'
        elif 'ot' in name_lower:
            return 'OT'
        else:
            return 'Unknown'
    
    def get_system_type_options(self) -> List[Tuple[str, str]]:
        return [(st['name'], st['display_name']) for st in self.system_types.values()]
    
    def get_system_type_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self.system_types.get(name)
    
    def get_icon_for_system_type(self, system_type: str) -> Tuple[Optional[str], str]:
        if not system_type:
            return None, '#808080'
        st = self.system_types.get(system_type)
        if st:
            icon_file = st.get('icon_filename')
            if icon_file and self.icon_exists(icon_file):
                return icon_file, st.get('fallback_color', '#808080')
            return None, st.get('fallback_color', '#808080')
        for name, st in self.system_types.items():
            if name.lower() == system_type.lower():
                icon_file = st.get('icon_filename')
                if icon_file and self.icon_exists(icon_file):
                    return icon_file, st.get('fallback_color', '#808080')
                return None, st.get('fallback_color', '#808080')
        system_type_lower = system_type.lower()
        for name, st in self.system_types.items():
            if system_type_lower in name.lower() or name.lower() in system_type_lower:
                icon_file = st.get('icon_filename')
                if icon_file and self.icon_exists(icon_file):
                    return icon_file, st.get('fallback_color', '#808080')
                return None, st.get('fallback_color', '#808080')
        return None, '#808080'
    
    def icon_exists(self, icon_filename: str) -> bool:
        if not icon_filename:
            return False
        icon_path = os.path.join(self.images_dir, icon_filename)
        return os.path.exists(icon_path)
    
    def add_system_type(self, name: str, display_name: str, category: str, 
                       icon_filename: str = None, fallback_color: str = '#808080',
                       description: str = '', sort_order: int = 0) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_types (name, display_name, category, icon_filename, 
                                       fallback_color, description, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, display_name, category, icon_filename, fallback_color, description, sort_order))
            conn.commit()
            self.load_system_types()
            self.logger.info(f"Added system type: {name}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding system type {name}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def update_system_type(self, system_type_id: int, **kwargs) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            set_clauses = []
            values = []
            for key, value in kwargs.items():
                if key in ['name', 'display_name', 'category', 'icon_filename', 
                          'fallback_color', 'description', 'is_active', 'sort_order']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            if not set_clauses:
                return False
            values.append(system_type_id)
            query = f"UPDATE system_types SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            self.load_system_types()
            self.logger.info(f"Updated system type ID: {system_type_id}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error updating system type {system_type_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_categories(self) -> List[str]:
        categories = set()
        for st in self.system_types.values():
            categories.add(st['category'])
        return sorted(list(categories))
    
    def get_system_types_by_category(self, category: str) -> List[Dict[str, Any]]:
        return [st for st in self.system_types.values() if st['category'] == category]
    
    def validate_icons(self) -> Dict[str, List[str]]:
        results = {
            'missing': [],
            'invalid': [],
            'valid': []
        }
        for name, st in self.system_types.items():
            icon_file = st.get('icon_filename')
            if not icon_file:
                results['missing'].append(f"{name}: No icon specified")
                continue
            icon_path = os.path.join(self.images_dir, icon_file)
            if not os.path.exists(icon_path):
                results['missing'].append(f"{name}: {icon_file}")
            else:
                results['valid'].append(f"{name}: {icon_file}")
        return results

class IconManager:
    def __init__(self, system_type_manager: SystemTypeManager):
        self.system_type_manager = system_type_manager
        self.icon_cache = {}
        self.images_dir = system_type_manager.images_dir
        self.logger = logging.getLogger(__name__)
        self.load_icons()
    
    def load_icons(self):
        try:
            for name, st in self.system_type_manager.system_types.items():
                icon_file = st.get('icon_filename')
                if icon_file:
                    icon_path = os.path.join(self.images_dir, icon_file)
                    if os.path.exists(icon_path):
                        try:
                            self.icon_cache[name] = mpimg.imread(icon_path)
                        except Exception as e:
                            self.logger.warning(f"Failed to load icon {icon_file}: {e}")
                            self.icon_cache[name] = self.create_fallback_icon(st['fallback_color'])
                    else:
                        self.icon_cache[name] = self.create_fallback_icon(st['fallback_color'])
                else:
                    self.icon_cache[name] = self.create_fallback_icon(st['fallback_color'])
            self.logger.info(f"Loaded {len(self.icon_cache)} icons into cache")
        except Exception as e:
            self.logger.error(f"Error loading icons: {e}")
            self.create_fallback_icons()
    
    def create_fallback_icon(self, color: str) -> Any:
        try:
            fig, ax = plt.subplots(figsize=(1, 1), dpi=64)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_aspect('equal')
            ax.axis('off')
            circle = Circle((0.5, 0.5), 0.4, color=color, alpha=0.8)
            ax.add_patch(circle)
            fig.canvas.draw()
            if hasattr(fig.canvas, 'tostring_rgb'):
                buf = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
                width, height = fig.canvas.get_width_height()
                buf = buf.reshape((height, width, 3))
            else:
                buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
                width, height = fig.canvas.get_width_height()
                buf = buf.reshape((height, width, 4))
                buf = buf[:, :, :3]
            plt.close(fig)
            return buf
        except Exception as e:
            self.logger.error(f"Error creating fallback icon: {e}")
            return np.full((64, 64, 3), [128, 128, 128], dtype=np.uint8)
    
    def create_fallback_icons(self):
        fallback_colors = {
            'Attacker-Machine': '#ff0000',
            'Server-DC': '#9932cc',
            'Server-Database': '#2ecc71',
            'Server-Web': '#e67e22',
            'Server-Application': '#8e44ad',
            'Server-File': '#34495e',
            'Server-Generic': '#e74c3c',
            'Server-Terminal SRV': '#e74c3c',
            'Gateway-Firewall': '#ff8c00',
            'Gateway-VPN': '#4169e1',
            'Gateway-Switch': '#00bfff',
            'Gateway-Router': '#ff6347',
            'Gateway-Web-Proxy': '#8a2be2',
            'Gateway-Email': '#ff69b4',
            'Gateway-DNS': '#1e90ff',
            'Gateway-Generic': '#ff6347',
            'Desktop': '#3498db',
            'Mobile': '#00ff7f',
            'OT-Device': '#ff8c42',
            'UnKnown': '#808080'
        }
        for name, color in fallback_colors.items():
            icon = self.create_fallback_icon(color)
            if icon is not None:
                self.icon_cache[name] = icon
            else:
                self.icon_cache[name] = np.full((64, 64, 3), [128, 128, 128], dtype=np.uint8)
    
    def get_icon(self, system_type: str) -> Any:
        if not system_type:
            icon = self.icon_cache.get('UnKnown')
            return icon if icon is not None else self.create_fallback_icon('#808080')
        if system_type in self.icon_cache:
            icon = self.icon_cache[system_type]
            return icon if icon is not None else self.create_fallback_icon('#808080')
        for name, icon in self.icon_cache.items():
            if name.lower() == system_type.lower():
                return icon if icon is not None else self.create_fallback_icon('#808080')
        system_type_lower = system_type.lower()
        for name, icon in self.icon_cache.items():
            if system_type_lower in name.lower() or name.lower() in system_type_lower:
                return icon if icon is not None else self.create_fallback_icon('#808080')
        icon = self.icon_cache.get('UnKnown')
        return icon if icon is not None else self.create_fallback_icon('#808080')
    
    def refresh_cache(self):
        self.icon_cache.clear()
        self.load_icons()

class EvidenceTypeManager:
    def __init__(self, db_path: str, parent_window=None):
        self.db_path = db_path
        self.parent_window = parent_window
        self.logger = logging.getLogger(__name__)
        self.evidence_type_window = None
    
    def add_evidence_type(self, evidence_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM EvidenceType WHERE evidencetype = ?", (evidence_type,))
            if cursor.fetchone()[0] > 0:
                return False
            cursor.execute("INSERT INTO EvidenceType (evidencetype, sort_order, source) VALUES (?, ?, ?)", (evidence_type, "0", "personal"))
            conn.commit()
            conn.close()
            self.logger.info(f"Added EvidenceType: {evidence_type}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding EvidenceType: {e}")
            return False
    
    def evidence_type_exists(self, evidence_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM EvidenceType WHERE evidencetype = ?", (evidence_type,))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error checking EvidenceType existence: {e}")
            return False
    
    def get_evidence_types(self) -> List[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT evidencetype, sort_order, source FROM EvidenceType ORDER BY sort_order, evidencetype")
            evidence_types = []
            for row in cursor.fetchall():
                evidence_types.append({
                    'evidencetype': row[0],
                    'sort_order': row[1],
                    'source': row[2]
                })
            conn.close()
            return evidence_types
        except sqlite3.Error as e:
            self.logger.error(f"Error getting EvidenceTypes: {e}")
            return []
    
    def show_add_evidence_type_dialog(self):
        if self.evidence_type_window is not None:
            self.evidence_type_window.activateWindow()
            self.evidence_type_window.raise_()
            return
        
        dialog = QWidget(self.parent_window)
        dialog.setWindowTitle("Add EvidenceType")
        dialog.setFixedSize(400, 200)
        dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.evidence_type_window = dialog
        original_close_event = dialog.closeEvent
        
        def custom_close_event(event):
            self.evidence_type_window = None
            if original_close_event:
                original_close_event(event)
        dialog.closeEvent = custom_close_event
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        label = QLabel("Enter new EvidenceType:")
        label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(label)
        text_input = QLineEdit()
        text_input.setPlaceholderText("e.g., Custom-Log-Type")
        text_input.setStyleSheet("padding: 8px; font-size: 11pt; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(text_input)
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Evidence Type")
        add_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        def add_evidence_type():
            evidence_type = text_input.text().strip()
            if not evidence_type:
                QMessageBox.warning(dialog, "Warning", "Please enter an EvidenceType name.")
                return
            if self.evidence_type_exists(evidence_type):
                QMessageBox.warning(dialog, "Warning", "EvidenceType already exists.")
                return
            if self.add_evidence_type(evidence_type):
                QMessageBox.information(dialog, "Success", f"EvidenceType '{evidence_type}' added successfully.")
                dialog.close()
            else:
                QMessageBox.critical(dialog, "Error", f"Failed to add EvidenceType: {evidence_type}")
        
        add_button.clicked.connect(add_evidence_type)
        cancel_button.clicked.connect(dialog.close)
        dialog.show()