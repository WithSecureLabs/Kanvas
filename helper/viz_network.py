# code Reviewed 
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QPushButton, QHBoxLayout
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

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

class IconManager:
    def __init__(self, system_type_manager=None):
        if system_type_manager is None:
            self.icon_cache = {}
            self._load_icons_hardcoded()
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
    
    def _load_icons_hardcoded(self):
        try:
            image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
            self.icon_cache["computer"] = mpimg.imread(os.path.join(image_dir, "computer_icon.png"))
            self.icon_cache["server"] = mpimg.imread(os.path.join(image_dir, "server_icon.png"))
            try:
                self.icon_cache["server-dc"] = mpimg.imread(os.path.join(image_dir, "dc.png"))
            except Exception as e:
                logger.warning(f"Failed to load domain controller icon: {e}")
                self.icon_cache["server-dc"] = self.create_circle_icon("#9932cc")
            try:
                self.icon_cache["desktop"] = mpimg.imread(os.path.join(image_dir, "computer_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load desktop icon: {e}")
                self.icon_cache["desktop"] = self.create_circle_icon("#ff0000")
            try:
                self.icon_cache["attacker-machine"] = mpimg.imread(os.path.join(image_dir, "attacker_logo.png"))
            except Exception as e:
                logger.warning(f"Failed to load attacker icon: {e}")
                self.icon_cache["attacker-machine"] = self.create_circle_icon("#ff0000")
            try:
                self.icon_cache["gateway-firewall"] = mpimg.imread(os.path.join(image_dir, "firewall_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load firewall icon: {e}")
                self.icon_cache["gateway-firewall"] = self.create_circle_icon("#ff8c00")
            try:
                self.icon_cache["gateway-vpn"] = mpimg.imread(os.path.join(image_dir, "vpn_logo.png"))
            except Exception as e:
                logger.warning(f"Failed to load VPN icon: {e}")
                self.icon_cache["gateway-vpn"] = self.create_circle_icon("#4169e1")
            try:
                self.icon_cache["gateway-switch"] = mpimg.imread(os.path.join(image_dir, "switch_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load switch icon: {e}")
                self.icon_cache["gateway-switch"] = self.create_circle_icon("#00bfff")
            try:
                self.icon_cache["gateway-router"] = mpimg.imread(os.path.join(image_dir, "router_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load router icon: {e}")
                self.icon_cache["gateway-router"] = self.create_circle_icon("#ff6347")
            try:
                self.icon_cache["gateway-web proxy"] = mpimg.imread(os.path.join(image_dir, "proxy_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load proxy icon: {e}")
                self.icon_cache["gateway-web proxy"] = self.create_circle_icon("#8a2be2")
            try:
                self.icon_cache["gateway-email"] = mpimg.imread(os.path.join(image_dir, "email_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load email icon: {e}")
                self.icon_cache["gateway-email"] = self.create_circle_icon("#ff69b4")
            try:
                self.icon_cache["gateway-dns"] = mpimg.imread(os.path.join(image_dir, "dns_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load DNS icon: {e}")
                self.icon_cache["gateway-dns"] = self.create_circle_icon("#1e90ff")
            try:
                self.icon_cache["server-database"] = mpimg.imread(os.path.join(image_dir, "database_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load database icon: {e}")
                self.icon_cache["server-database"] = self.create_circle_icon("#2ecc71")
            try:
                self.icon_cache["server-web"] = mpimg.imread(os.path.join(image_dir, "webserver_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load web server icon: {e}")
                self.icon_cache["server-web"] = self.create_circle_icon("#e67e22")
            try:
                self.icon_cache["server-file"] = mpimg.imread(os.path.join(image_dir, "fileserver_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load file server icon: {e}")
                self.icon_cache["server-file"] = self.create_circle_icon("#34495e")
            try:
                self.icon_cache["server-application"] = mpimg.imread(os.path.join(image_dir, "appserver_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load application server icon: {e}")
                self.icon_cache["server-application"] = self.create_circle_icon("#8e44ad")
            try:
                self.icon_cache["ot device"] = mpimg.imread(os.path.join(image_dir, "ot_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load OT device icon: {e}")
                self.icon_cache["ot device"] = self.create_circle_icon("#ff8c42")
            try:
                self.icon_cache["mobile"] = mpimg.imread(os.path.join(image_dir, "mobile_icon.png"))
            except Exception as e:
                logger.warning(f"Failed to load mobile icon: {e}")
                self.icon_cache["mobile"] = self.create_circle_icon("#00ff7f")
            try:
                self.icon_cache["unknown"] = mpimg.imread(os.path.join(image_dir, "unknown.png"))
            except Exception as e:
                logger.warning(f"Failed to load unknown icon: {e}")
                self.icon_cache["unknown"] = self.create_circle_icon("#808080")
        except Exception as e:
            logger.warning(f"Failed to load icon images: {e}")
            self.icon_cache["computer"] = self.create_circle_icon("#3498db")
            self.icon_cache["server"] = self.create_circle_icon("#e74c3c")
            self.icon_cache["server-dc"] = self.create_circle_icon("#9932cc")
            self.icon_cache["attacker-machine"] = self.create_circle_icon("#ff0000")
            self.icon_cache["gateway-firewall"] = self.create_circle_icon("#ff8c00")
            self.icon_cache["gateway-vpn"] = self.create_circle_icon("#4169e1")
            self.icon_cache["gateway-switch"] = self.create_circle_icon("#00bfff")
            self.icon_cache["gateway-router"] = self.create_circle_icon("#ff6347")
            self.icon_cache["gateway-web proxy"] = self.create_circle_icon("#8a2be2")
            self.icon_cache["gateway-email"] = self.create_circle_icon("#ff69b4")
            self.icon_cache["gateway-dns"] = self.create_circle_icon("#1e90ff")
            self.icon_cache["server-database"] = self.create_circle_icon("#2ecc71")
            self.icon_cache["server-web"] = self.create_circle_icon("#e67e22")
            self.icon_cache["server-file"] = self.create_circle_icon("#34495e")
            self.icon_cache["server-application"] = self.create_circle_icon("#8e44ad")
            self.icon_cache["ot device"] = self.create_circle_icon("#ff8c42")
            self.icon_cache["mobile"] = self.create_circle_icon("#00ff7f")
            self.icon_cache["unknown"] = self.create_circle_icon("#808080")

    def get_icon(self, system_type):
        if hasattr(self, 'database_icon_manager'):
            # Use database-driven approach
            return self.database_icon_manager.get_icon(system_type)
        else:
            # Fallback to hardcoded approach
            if system_type and system_type.lower() == "server-dc":
                return self.icon_cache["server-dc"]
            elif system_type and system_type.lower() == "server-database":
                return self.icon_cache["server-database"]
            elif system_type and system_type.lower() == "server-web":
                return self.icon_cache["server-web"]
            elif system_type and system_type.lower() == "server-file":
                return self.icon_cache["server-file"]
            elif system_type and system_type.lower() == "server-application":
                return self.icon_cache["server-application"]
            elif system_type and system_type.lower() == "gateway-firewall":
                return self.icon_cache["gateway-firewall"]
            elif system_type and system_type.lower() == "gateway-vpn":
                return self.icon_cache["gateway-vpn"]
            elif system_type and system_type.lower() == "gateway-switch":
                return self.icon_cache["gateway-switch"]
            elif system_type and system_type.lower() == "gateway-router":
                return self.icon_cache["gateway-router"]
            elif system_type and system_type.lower() == "gateway-web proxy":
                return self.icon_cache["gateway-web proxy"]
            elif system_type and system_type.lower() == "gateway-email":
                return self.icon_cache["gateway-email"]
            elif system_type and system_type.lower() == "gateway-dns":
                return self.icon_cache["gateway-dns"]
            elif system_type and system_type.lower() == "ot device":
                return self.icon_cache["ot device"]
            elif system_type and system_type.lower() == "mobile":
                return self.icon_cache["mobile"]
            elif system_type and system_type.lower() == "unknown":
                return self.icon_cache["unknown"]
            elif system_type and "attacker" in system_type.lower():
                return self.icon_cache["attacker-machine"]
            elif system_type and "server" in system_type.lower():
                return self.icon_cache["server"]
            else:
                return self.icon_cache["computer"]

class SystemTypeLoader:
    def __init__(self, workbook):
        self.workbook = workbook
        self.system_types = {}
    
    def load_system_types(self):
        try:
            systems_sheet = self.workbook["Systems"]
            systems_headers = [cell.value for cell in systems_sheet[1]]
            hostname_idx = systems_headers.index("HostName") if "HostName" in systems_headers else -1
            ipaddress_idx = systems_headers.index("IPAddress") if "IPAddress" in systems_headers else -1
            systemtype_idx = systems_headers.index("SystemType") if "SystemType" in systems_headers else -1
            if hostname_idx == -1 or systemtype_idx == -1:
                logger.warning("Required columns not found in Systems sheet")
            else:
                for row_idx in range(2, systems_sheet.max_row + 1):
                    hostname = systems_sheet.cell(row=row_idx, column=hostname_idx + 1).value
                    system_type = systems_sheet.cell(row=row_idx, column=systemtype_idx + 1).value
                    if not hostname or not system_type:
                        continue
                    hostname = str(hostname).strip()
                    system_type = str(system_type).strip()
                    self.system_types[hostname.lower()] = system_type
                    self.system_types[hostname] = system_type
            if ipaddress_idx != -1:
                for row_idx in range(2, systems_sheet.max_row + 1):
                    ipaddress = systems_sheet.cell(row=row_idx, column=ipaddress_idx + 1).value
                    system_type = systems_sheet.cell(row=row_idx, column=systemtype_idx + 1).value
                    if not ipaddress or not system_type:
                        continue
                    ipaddress = str(ipaddress).strip()
                    system_type = str(system_type).strip()
                    self.system_types[ipaddress.lower()] = system_type
                    self.system_types[ipaddress] = system_type
        except Exception as e:
            logger.warning(f"Error loading system types from Systems sheet: {e}")
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
            rows_processed += 1
            visualize_value = self.sheet.cell(row=row_idx, column=self.column_indices['Visualize'] + 1).value
            if str(visualize_value).lower() != "yes":
                continue
            event_system = self.sheet.cell(row=row_idx, column=self.column_indices['Event System'] + 1).value
            remote_system = self.sheet.cell(row=row_idx, column=self.column_indices['Remote System'] + 1).value
            direction = self.sheet.cell(row=row_idx, column=self.column_indices['<->'] + 1).value
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
    
    def draw_network(self, seed=None):
        self.ax.clear()
        self.fig.patch.set_facecolor('white')
        if seed is None:
            seed = np.random.randint(1, 1000)
        self.pos = nx.spring_layout(self.G, k=0.8, scale=0.9, seed=seed)
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
        redraw_button = QPushButton("⟳ Redraw Network")
        redraw_button.setToolTip("Generate a different layout arrangement")
        redraw_button.setStyleSheet("""
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
        """)
        toolbar.addSeparator()
        toolbar.addWidget(redraw_button)
        self.renderer = NetworkRenderer(self.G, self.icon_manager, self.fig, ax, self.canvas)
        redraw_button.clicked.connect(lambda: self.renderer.draw_network(seed=np.random.randint(1, 1000)))
        layout = QVBoxLayout(self.vis_window)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)  
        self.vis_window.setLayout(layout)
        self.renderer.draw_network(seed=42)
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
            sheet_name = "Timeline"
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
            required_columns = ["Event System", "Remote System", "<->", "Visualize"]
            column_indices = {}
            for col_name in required_columns:
                if col_name in headers:
                    column_indices[col_name] = headers.index(col_name)
                else:
                    QMessageBox.critical(window, "Error", f"Column '{col_name}' not found in Timeline sheet headers.")
                    logger.error(f"Column '{col_name}' not found in Timeline sheet")
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