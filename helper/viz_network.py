# code Reviewed 
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QComboBox, QLabel
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
import os
import logging
from matplotlib.patches import FancyArrowPatch
from helper.system_type import SystemTypeManager, IconManager as DatabaseIconManager

# Default images dir relative to project root
_IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

from helper import config, styles

class IconManager:
    def __init__(self, system_type_manager=None):
        if system_type_manager is None:
            stm = SystemTypeManager.from_yaml_only(_IMAGES_DIR)
            self.database_icon_manager = DatabaseIconManager(stm)
            self.icon_cache = self.database_icon_manager.icon_cache
        else:
            self.database_icon_manager = DatabaseIconManager(system_type_manager)
            self.icon_cache = self.database_icon_manager.icon_cache
    
    def create_circle_icon(self, color):
        fig = plt.figure(figsize=(1, 1))
        fig.patch.set_alpha(0)
        ax = fig.add_subplot(111)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        circle = plt.Circle((0.5, 0.5), 0.4, color=color)
        ax.add_patch(circle)
        ax.axis('off')
        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(fig)  
        return img
    
    def get_icon(self, system_type):
        return self.database_icon_manager.get_icon(system_type)

class SystemTypeLoader:
    def __init__(self, workbook):
        self.workbook = workbook
        self.system_types = {}
    
    def load_system_types(self):
        try:
            systems_sheet = self.workbook[config.SHEET_SYSTEMS]
            systems_headers = [cell.value for cell in systems_sheet[1]]
            hostname_idx = systems_headers.index(config.COL_HOSTNAME) if config.COL_HOSTNAME in systems_headers else -1
            ip_idx = systems_headers.index(config.COL_IP_ADDRESS) if config.COL_IP_ADDRESS in systems_headers else -1
            type_idx = systems_headers.index(config.COL_SYSTEM_TYPE) if config.COL_SYSTEM_TYPE in systems_headers else -1
            if hostname_idx == -1 or type_idx == -1:
                logger.warning(f"Required columns '{config.COL_HOSTNAME}' or '{config.COL_SYSTEM_TYPE}' not found in {config.SHEET_SYSTEMS} sheet")
            else:
                for row_idx in range(2, systems_sheet.max_row + 1):
                    hostname = systems_sheet.cell(row=row_idx, column=hostname_idx + 1).value
                    system_type = systems_sheet.cell(row=row_idx, column=type_idx + 1).value
                    if not hostname or not system_type:
                        continue
                    hostname = str(hostname).strip()
                    system_type = str(system_type).strip()
                    self.system_types[hostname.lower()] = system_type
                    self.system_types[hostname] = system_type
            if ip_idx != -1:
                for row_idx in range(2, systems_sheet.max_row + 1):
                    ipaddress = systems_sheet.cell(row=row_idx, column=ip_idx + 1).value
                    system_type = systems_sheet.cell(row=row_idx, column=type_idx + 1).value
                    if not ipaddress or not system_type:
                        continue
                    ipaddress = str(ipaddress).strip()
                    system_type = str(system_type).strip()
                    self.system_types[ipaddress.lower()] = system_type
                    self.system_types[ipaddress] = system_type
        except Exception as e:
            logger.warning(f"Error loading system types from {config.SHEET_SYSTEMS} sheet: {e}")
            self.system_types = {}
        return self.system_types

class NetworkGraphBuilder:
    def __init__(self, sheet, column_indices, system_types):
        self.sheet = sheet
        self.column_indices = column_indices
        self.system_types = system_types
        self.G = nx.DiGraph()
    
    def build_graph(self):
        rows_processed = 0
        rows_visualized = 0
        for row_idx in range(2, self.sheet.max_row + 1):
            visualize_value = self.sheet.cell(row=row_idx, column=self.column_indices[config.COL_VISUALIZE] + 1).value
            if str(visualize_value).lower() != config.VAL_VISUALIZE_YES:
                continue
            event_system = self.sheet.cell(row=row_idx, column=self.column_indices[config.COL_EVENT_SYSTEM] + 1).value
            remote_system = self.sheet.cell(row=row_idx, column=self.column_indices[config.COL_REMOTE_SYSTEM] + 1).value
            direction = self.sheet.cell(row=row_idx, column=self.column_indices[config.COL_DIRECTION] + 1).value
            if event_system and remote_system and direction:
                rows_visualized += 1
                event_system = str(event_system).strip()
                remote_system = str(remote_system).strip()
                direction = str(direction).strip()
                event_system_type = "unknown"
                remote_system_type = "unknown"
                if event_system in self.system_types:
                    event_system_type = self.system_types[event_system]
                    logger.debug(f"Found direct match for {event_system}: {event_system_type}")
                elif event_system.lower() in self.system_types:
                    event_system_type = self.system_types[event_system.lower()]
                    logger.debug(f"Found lowercase match for {event_system}: {event_system_type}")
                if remote_system in self.system_types:
                    remote_system_type = self.system_types[remote_system]
                    logger.debug(f"Found direct match for {remote_system}: {remote_system_type}")
                elif remote_system.lower() in self.system_types:
                    remote_system_type = self.system_types[remote_system.lower()]
                    logger.debug(f"Found lowercase match for {remote_system}: {remote_system_type}")
                logger.debug(f"Adding connection: {event_system} ({event_system_type}) {direction} {remote_system} ({remote_system_type})")
                self.G.add_node(event_system, label=event_system, node_type=event_system_type)
                self.G.add_node(remote_system, label=remote_system, node_type=remote_system_type)
                if direction == "->":
                    self.G.add_edge(event_system, remote_system, label="->")
                elif direction == "<-":
                    self.G.add_edge(remote_system, event_system, label="<-")
                elif direction == "<->":
                    self.G.add_edge(event_system, remote_system, label="<->")
                    self.G.add_edge(remote_system, event_system, label="<->")
        logger.info(f"Processed {rows_processed} rows, visualizing {rows_visualized} connections")
        logger.info(f"Graph created with {len(self.G.nodes)} nodes and {len(self.G.edges)} edges")
        return self.G

class NetworkRenderer:
    def __init__(self, graph, icon_manager, fig, ax, canvas):
        self.G = graph
        self.icon_manager = icon_manager
        self.fig = fig
        self.ax = ax
        self.canvas = canvas
        self.pos = None
        self.grouping_mode = "none"  # Default: no grouping
    
    def _get_grouped_layout(self, seed=None):
        """Generate layout with grouping based on system_type"""
        if self.grouping_mode == "none":
            # Standard spring layout
            return nx.spring_layout(self.G, k=0.8, scale=0.9, seed=seed)
        
        # Group nodes by system_type
        nodes_by_type = {}
        for node in self.G.nodes():
            system_type = self.G.nodes[node].get("node_type", "unknown")
            if system_type not in nodes_by_type:
                nodes_by_type[system_type] = []
            nodes_by_type[system_type].append(node)
        
        if self.grouping_mode == "circular":
            # Circular grouping: each type on a circle
            pos = {}
            num_types = len(nodes_by_type)
            if num_types == 0:
                return nx.spring_layout(self.G, k=0.8, scale=0.9, seed=seed)
            
            radius = 1.5
            angle_step = 2 * np.pi / num_types if num_types > 1 else 0
            
            for idx, (system_type, nodes) in enumerate(nodes_by_type.items()):
                center_angle = idx * angle_step
                center_x = radius * np.cos(center_angle)
                center_y = radius * np.sin(center_angle)
                
                # Position nodes in a small circle around the type center
                num_nodes = len(nodes)
                if num_nodes == 1:
                    pos[nodes[0]] = (center_x, center_y)
                else:
                    node_radius = 0.3
                    node_angle_step = 2 * np.pi / num_nodes
                    for node_idx, node in enumerate(nodes):
                        node_angle = node_idx * node_angle_step
                        node_x = center_x + node_radius * np.cos(node_angle)
                        node_y = center_y + node_radius * np.sin(node_angle)
                        pos[node] = (node_x, node_y)
            
            # Use spring layout as initial positions, then adjust
            initial_pos = nx.spring_layout(self.G, k=0.8, scale=0.9, seed=seed)
            # Blend initial positions with grouped positions
            for node in self.G.nodes():
                if node in pos:
                    # 70% grouped position, 30% spring position for smooth edges
                    pos[node] = (
                        0.7 * pos[node][0] + 0.3 * initial_pos[node][0],
                        0.7 * pos[node][1] + 0.3 * initial_pos[node][1]
                    )
            
            return pos
        
        elif self.grouping_mode == "grid":
            # Grid-based grouping
            pos = {}
            num_types = len(nodes_by_type)
            if num_types == 0:
                return nx.spring_layout(self.G, k=0.8, scale=0.9, seed=seed)
            
            # Calculate grid dimensions
            cols = int(np.ceil(np.sqrt(num_types)))
            rows = int(np.ceil(num_types / cols))
            
            cell_width = 1.5
            cell_height = 1.5
            
            for idx, (system_type, nodes) in enumerate(nodes_by_type.items()):
                row = idx // cols
                col = idx % cols
                center_x = (col - cols/2 + 0.5) * cell_width
                center_y = (rows/2 - row - 0.5) * cell_height
                
                # Position nodes in a grid within the cell
                num_nodes = len(nodes)
                if num_nodes == 1:
                    pos[nodes[0]] = (center_x, center_y)
                else:
                    sub_cols = int(np.ceil(np.sqrt(num_nodes)))
                    sub_rows = int(np.ceil(num_nodes / sub_cols))
                    sub_cell_size = 0.15
                    
                    for node_idx, node in enumerate(nodes):
                        sub_row = node_idx // sub_cols
                        sub_col = node_idx % sub_cols
                        node_x = center_x + (sub_col - sub_cols/2 + 0.5) * sub_cell_size
                        node_y = center_y + (sub_rows/2 - sub_row - 0.5) * sub_cell_size
                        pos[node] = (node_x, node_y)
            
            return pos
        
        elif self.grouping_mode == "constrained_spring":
            # Constrained spring: add extra edges between same-type nodes
            G_enhanced = self.G.copy()
            for system_type, nodes in nodes_by_type.items():
                if len(nodes) > 1:
                    # Add weak edges between nodes of same type to pull them together
                    for i, node1 in enumerate(nodes):
                        for node2 in nodes[i+1:]:
                            if not G_enhanced.has_edge(node1, node2):
                                G_enhanced.add_edge(node1, node2, weight=0.1)
            
            # Use spring layout with adjusted parameters
            pos = nx.spring_layout(G_enhanced, k=0.6, scale=0.9, seed=seed, iterations=100)
            return pos
        
        else:
            # Fallback to standard layout
            return nx.spring_layout(self.G, k=0.8, scale=0.9, seed=seed)
    
    def draw_network(self, seed=None, grouping_mode=None):
        self.ax.clear()
        self.fig.patch.set_facecolor('white')
        
        # Update grouping mode if provided
        if grouping_mode is not None:
            self.grouping_mode = grouping_mode
        
        if seed is None:
            seed = np.random.randint(1, 1000)
        
        self.pos = self._get_grouped_layout(seed=seed)
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        self.ax.set_xlim(min(x for x, y in self.pos.values()) - 0.2, max(x for x, y in self.pos.values()) + 0.2)
        self.ax.set_ylim(min(y for x, y in self.pos.values()) - 0.2, max(y for x, y in self.pos.values()) + 0.2)
        for node, (x, y) in self.pos.items():
            system_type = self.G.nodes[node].get("node_type", "unknown")
            icon = self.icon_manager.get_icon(system_type)
            # if system_type and system_type.lower() == "server-dc":
            #     print(f"Using DC icon for {node}")
            # elif system_type and "attacker" in system_type.lower():
            #     print(f"Using attacker icon for {node}")
            # elif system_type and "server" in system_type.lower():
            #     print(f"Using server icon for {node}")
            # else:
            #     print(f"Using computer icon for {node}")
            imagebox = OffsetImage(icon, zoom=0.08)  
            ab = AnnotationBbox(imagebox, (x, y), frameon=False, pad=0.0)
            self.ax.add_artist(ab)
        for u, v, data in self.G.edges(data=True):
            posA = self.pos[u]
            posB = self.pos[v]
            if data.get("label") == "<->":
                color = "darkgreen"
                width = 2.0
                connectionstyle = "arc3,rad=0.2"
                arrowsize = 20
            else:
                color = "gray" 
                width = 1.5
                connectionstyle = "arc3,rad=0.1"
                arrowsize = 15
            arrow = FancyArrowPatch(
                posA, posB,
                arrowstyle=f'-|>',
                connectionstyle=connectionstyle,
                mutation_scale=arrowsize,
                linewidth=width,
                color=color,
                zorder=10
            )
            self.ax.add_patch(arrow)
        label_pos = {node: (coords[0], coords[1] - 0.10) for node, coords in self.pos.items()}
        nx.draw_networkx_labels(self.G, label_pos, labels={n: n for n in self.G.nodes()},
                              font_size=9, font_weight='normal',
                              bbox=dict(facecolor='white', edgecolor='gray', alpha=0.9, pad=1, boxstyle="round,pad=0.2"))
        plt.title("Lateral Movemnt", fontsize=14)
        self.ax.set_axis_off()
        plt.tight_layout()
        self.canvas.draw()

class NetworkVisualizationDialog:
    def __init__(self, parent_window, graph, icon_manager):
        self.parent_window = parent_window
        self.G = graph
        self.icon_manager = icon_manager
        self.vis_window = None
        self.renderer = None
        self.fig = None  
        self.canvas = None  
        
    def create_dialog(self):
        self.vis_window = QDialog(self.parent_window)
        self.vis_window.setWindowTitle("Network Visualization")
        self.vis_window.resize(1100, 800)
        self.vis_window.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint
        )
        self.vis_window.setModal(False)

        def on_close():
            if self.fig is not None:
                plt.close(self.fig)
                self.fig = None
            if self.canvas is not None:
                self.canvas.deleteLater()
                self.canvas = None
            self.vis_window.deleteLater()
            
        self.vis_window.finished.connect(on_close)
        self.fig, ax = plt.subplots(figsize=(11, 8))
        self.canvas = FigureCanvas(self.fig)
        toolbar = NavigationToolbar2QT(self.canvas, self.vis_window)
        
        # Grouping mode selector
        grouping_label = QLabel("Group by Type:")
        grouping_label.setStyleSheet(styles.STYLE_MARGIN_HORIZONTAL)
        self.grouping_combo = QComboBox()
        self.grouping_combo.addItems([
            "None (Standard Layout)",
            "Circular Grouping",
            "Grid Grouping",
            "Constrained Spring"
        ])
        self.grouping_combo.setCurrentIndex(0)
        self.grouping_combo.setToolTip("Select how to group nodes by system type")
        self.grouping_combo.setMinimumWidth(180)
        self.grouping_combo.setStyleSheet(styles.COMBOBOX_STYLE)
        
        # Enable grouping checkbox
        self.grouping_enabled = QCheckBox("Enable Grouping")
        self.grouping_enabled.setChecked(False)
        self.grouping_enabled.setToolTip("Toggle grouping on/off")
        self.grouping_enabled.setStyleSheet(styles.STYLE_MARGIN_HORIZONTAL)
        
        # Redraw button
        redraw_button = QPushButton("⟳ Redraw Network")
        redraw_button.setToolTip("Generate a different layout arrangement")
        redraw_button.setStyleSheet(styles.BUTTON_STYLE_NEUTRAL)
        
        toolbar.addSeparator()
        toolbar.addWidget(self.grouping_enabled)
        toolbar.addWidget(grouping_label)
        toolbar.addWidget(self.grouping_combo)
        toolbar.addSeparator()
        toolbar.addWidget(redraw_button)
        
        self.renderer = NetworkRenderer(self.G, self.icon_manager, self.fig, ax, self.canvas)
        
        # Function to get current grouping mode
        def get_current_grouping_mode():
            if self.grouping_enabled.isChecked():
                mode_map = {
                    0: "none",
                    1: "circular",
                    2: "grid",
                    3: "constrained_spring"
                }
                return mode_map.get(self.grouping_combo.currentIndex(), "none")
            return "none"
        
        # Function to redraw with current settings
        def redraw_network():
            grouping_mode = get_current_grouping_mode()
            self.renderer.draw_network(seed=np.random.randint(1, 1000), grouping_mode=grouping_mode)
        
        # Connect signals
        redraw_button.clicked.connect(redraw_network)
        self.grouping_combo.currentIndexChanged.connect(lambda: redraw_network() if self.grouping_enabled.isChecked() else None)
        self.grouping_enabled.toggled.connect(redraw_network)
        
        layout = QVBoxLayout(self.vis_window)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)  
        self.vis_window.setLayout(layout)
        self.renderer.draw_network(seed=42, grouping_mode="none")
        self.vis_window.show()  

class NetworkVisualizer:
    def __init__(self, system_type_manager=None):
        self.icon_manager = IconManager(system_type_manager)
    
    def visualize_network(self, window):
        try:
            if not hasattr(window, "current_workbook") or not hasattr(window, "current_file_path"):
                QMessageBox.warning(window, "Error", "No Excel file loaded. Please load a file first.")
                return None
            workbook = window.current_workbook
            sheet_name = config.SHEET_TIMELINE
            if sheet_name not in workbook.sheetnames:
                QMessageBox.critical(window, "Error", f"Sheet '{sheet_name}' not found in the workbook.")
                logger.error(f"Sheet '{sheet_name}' not found in workbook: {window.current_file_path}")
                return None
            try:
                sheet = workbook[sheet_name]
                headers = [cell.value for cell in sheet[1]]
                headers = [str(header) if header else f"Column {i+1}" for i, header in enumerate(headers)]
            except Exception as e:
                QMessageBox.critical(window, "Error", f"Failed to read sheet headers: {str(e)}")
                logger.error(f"Failed to read sheet headers: {str(e)}")
                return None
            required_columns = [config.COL_EVENT_SYSTEM, config.COL_REMOTE_SYSTEM, config.COL_DIRECTION, config.COL_VISUALIZE]
            column_indices = {}
            for col_name in required_columns:
                if col_name in headers:
                    column_indices[col_name] = headers.index(col_name)
                else:
                    QMessageBox.critical(window, "Error", f"Column '{col_name}' not found in {config.SHEET_TIMELINE} sheet headers.")
                    logger.error(f"Column '{col_name}' not found in {config.SHEET_TIMELINE} sheet")
                    return None
            system_type_loader = SystemTypeLoader(workbook)
            system_types = system_type_loader.load_system_types()
            graph_builder = NetworkGraphBuilder(sheet, column_indices, system_types)
            G = graph_builder.build_graph()
            if not G.nodes:
                QMessageBox.information(window, "Info", "No data to visualize.")
                return
            dialog = NetworkVisualizationDialog(window, G, self.icon_manager)
            dialog.create_dialog()
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Failed to visualize network: {str(e)}")
            logger.error(f"Failed to visualize network: {str(e)}")
            return None
        
def visualize_network(window, system_type_manager=None):
    visualizer = NetworkVisualizer(system_type_manager)
    visualizer.visualize_network(window)