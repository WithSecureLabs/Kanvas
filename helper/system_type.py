# system_type.py: system type and evidence type management for Kanvas. SystemTypeManager
# loads and caches system types (Attacker, Server, Gateway, Client, OT, etc.) from SQLite,
# provides icons and fallback colors for timeline/network views. EvidenceTypeManager handles
# evidence type CRUD and add-dialog. IconManager loads image icons or generates fallback circles.
# Revised on 01/02/2026 by Jinto Antony

import logging
import sqlite3
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from helper import styles

logger = logging.getLogger(__name__)

SYSTEM_TYPES_YAML_PATH = Path(__file__).resolve().parent / "system_types.yaml"


def _load_system_types_from_yaml() -> List[Dict[str, Any]]:
    """Load default system types from helper/system_types.yaml."""
    try:
        with open(SYSTEM_TYPES_YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "default_system_types" in data:
            return data["default_system_types"]
    except (yaml.YAMLError, OSError) as e:
        logger.warning("Could not load system_types.yaml: %s", e)
    return []


def load_icon_mapping_from_db(db_path: str) -> Dict[str, str]:
    """Load system type name -> icon_filename mapping from database for report generation."""
    mapping = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, icon_filename FROM system_types WHERE is_active = 1 AND icon_filename IS NOT NULL AND icon_filename != ''"
        )
        for row in cursor.fetchall():
            name, icon_file = row[0], row[1]
            if name and icon_file:
                mapping[name.lower().strip()] = icon_file.strip()
                mapping[name.strip()] = icon_file.strip()
        conn.close()
    except sqlite3.Error as e:
        logger.warning("Could not load icon mapping from DB: %s", e)
    return mapping


class SystemTypeManager:
    @classmethod
    def from_yaml_only(cls, images_dir: str = "images") -> "SystemTypeManager":
        """Create a SystemTypeManager with types loaded from system_types.yaml (no DB)."""
        instance = object.__new__(cls)
        instance.db_path = ""
        instance.images_dir = Path(images_dir)
        instance.system_types = {}
        instance.cache_ttl = 3600
        instance.last_cache_update = 0
        yaml_types = _load_system_types_from_yaml()
        for i, t in enumerate(yaml_types):
            name = t.get("name", "")
            if name:
                instance.system_types[name] = {
                    "id": i + 1,
                    "name": name,
                    "display_name": t.get("display_name", name.replace("-", " ")),
                    "category": t.get("category", "Unknown"),
                    "icon_filename": t.get("icon_filename"),
                    "fallback_color": t.get("fallback_color", "#808080"),
                    "description": t.get("description", ""),
                    "is_active": True,
                    "sort_order": t.get("sort_order", i + 1),
                }
        return instance

    def __init__(self, db_path: str, images_dir: str = "images"):
        self.db_path = db_path
        self.images_dir = Path(images_dir)
        self.system_types = {}
        self.cache_ttl = 3600
        self.last_cache_update = 0
        self.populate_default_system_types()
        self.load_system_types()
    
    def populate_default_system_types(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM system_types")
            count = cursor.fetchone()[0]
            if count == 0:
                default_types = _load_system_types_from_yaml()
                if default_types:
                    rows = [
                        (
                            t["name"],
                            t["display_name"],
                            t["category"],
                            t.get("icon_filename"),
                            t.get("fallback_color", "#808080"),
                            t.get("description", ""),
                            t.get("sort_order", 0),
                        )
                        for t in default_types
                    ]
                    cursor.executemany("""
                        INSERT INTO system_types (name, display_name, category, icon_filename, fallback_color, description, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, rows)
                    conn.commit()
                    logger.info("Populated %s default system types from system_types.yaml", len(rows))
        except sqlite3.Error as e:
            logger.error("Error populating default system types: %s", e)
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
            logger.info("Loaded %s system types from database", len(self.system_types))
        except sqlite3.Error as e:
            logger.error("Error loading system types: %s", e)
            self.load_fallback_system_types()
        finally:
            if conn:
                conn.close()
    
    def load_fallback_system_types(self):
        self.system_types = {}
        yaml_types = _load_system_types_from_yaml()
        if yaml_types:
            for i, t in enumerate(yaml_types):
                name = t.get("name", "")
                if name:
                    self.system_types[name] = {
                        "id": i + 1,
                        "name": name,
                        "display_name": t.get("display_name", name.replace("-", " ")),
                        "category": t.get("category", self.guess_category(name)),
                        "icon_filename": t.get("icon_filename"),
                        "fallback_color": t.get("fallback_color", "#808080"),
                        "description": t.get("description", f"System type: {name}"),
                        "is_active": True,
                        "sort_order": t.get("sort_order", i + 1),
                    }
            logger.warning("Using fallback system types from system_types.yaml (database unavailable)")
    
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
        return (self.images_dir / icon_filename).is_file()
    
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
            logger.info("Added system type: %s", name)
            return True
        except sqlite3.Error as e:
            logger.error("Error adding system type %s: %s", name, e)
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
            logger.info("Updated system type ID: %s", system_type_id)
            return True
        except sqlite3.Error as e:
            logger.error("Error updating system type %s: %s", system_type_id, e)
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
                results["missing"].append("%s: No icon specified" % name)
                continue
            icon_path = self.images_dir / icon_file
            if not icon_path.is_file():
                results["missing"].append("%s: %s" % (name, icon_file))
            else:
                results["valid"].append("%s: %s" % (name, icon_file))
        return results

class IconManager:
    def __init__(self, system_type_manager: SystemTypeManager):
        self.system_type_manager = system_type_manager
        self.icon_cache = {}
        self.images_dir = system_type_manager.images_dir
        self.load_icons()

    def load_icons(self):
        try:
            for name, st in self.system_type_manager.system_types.items():
                icon_file = st.get("icon_filename")
                if icon_file:
                    icon_path = self.images_dir / icon_file
                    if icon_path.is_file():
                        try:
                            self.icon_cache[name] = mpimg.imread(str(icon_path))
                        except Exception as e:
                            logger.warning("Failed to load icon %s: %s", icon_file, e)
                            self.icon_cache[name] = self.create_fallback_icon(st["fallback_color"])
                    else:
                        self.icon_cache[name] = self.create_fallback_icon(st["fallback_color"])
                else:
                    self.icon_cache[name] = self.create_fallback_icon(st["fallback_color"])
            logger.info("Loaded %s icons into cache", len(self.icon_cache))
        except Exception as e:
            logger.error("Error loading icons: %s", e)
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
            logger.error("Error creating fallback icon: %s", e)
            return np.full((64, 64, 3), [128, 128, 128], dtype=np.uint8)
    
    def create_fallback_icons(self):
        yaml_types = _load_system_types_from_yaml()
        fallback_colors = {}
        for t in yaml_types:
            name = t.get("name")
            if name:
                fallback_colors[name] = t.get("fallback_color", "#808080")
        if not fallback_colors:
            fallback_colors["UnKnown"] = "#808080"
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
        self.evidence_type_window = None

    def add_evidence_type(self, evidence_type: str) -> bool:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM EvidenceType WHERE evidencetype = ?", (evidence_type,))
            if cursor.fetchone()[0] > 0:
                return False
            cursor.execute(
                "INSERT INTO EvidenceType (evidencetype, sort_order, source) VALUES (?, ?, ?)",
                (evidence_type, "0", "personal"),
            )
            conn.commit()
            logger.info("Added EvidenceType: %s", evidence_type)
            return True
        except sqlite3.Error as e:
            logger.error("Error adding EvidenceType: %s", e)
            return False
        finally:
            if conn:
                conn.close()

    def evidence_type_exists(self, evidence_type: str) -> bool:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM EvidenceType WHERE evidencetype = ?", (evidence_type,))
            return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logger.error("Error checking EvidenceType existence: %s", e)
            return False
        finally:
            if conn:
                conn.close()

    def get_evidence_types(self) -> List[Dict[str, Any]]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT evidencetype, sort_order, source FROM EvidenceType ORDER BY sort_order, evidencetype"
            )
            return [
                {"evidencetype": row[0], "sort_order": row[1], "source": row[2]}
                for row in cursor.fetchall()
            ]
        except sqlite3.Error as e:
            logger.error("Error getting EvidenceTypes: %s", e)
            return []
        finally:
            if conn:
                conn.close()
    
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
        text_input.setStyleSheet(styles.INPUT_LINE_STYLE)
        layout.addWidget(text_input)
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Evidence Type")
        add_button.setStyleSheet(styles.BUTTON_STYLE_BASE)
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(styles.BUTTON_STYLE_DANGER)
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