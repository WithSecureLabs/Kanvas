"""
Generates report visualizations for Kanvas: timeline and network graphs from
workbook sheets, MITRE statistics, and icon data URLs for vis.js. Cross-platform
(Windows, macOS, Linux). Icon mappings are read from the database when available,
otherwise from helper/system_types.yaml.
"""

import base64
import logging
import tempfile
import warnings
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx

from helper import config
from helper.system_type import load_icon_mapping_from_db, _load_system_types_from_yaml

matplotlib.use("Agg")

logger = logging.getLogger(__name__)

MAX_TIMELINE_ROWS = 1000
MAX_NETWORK_ROWS = 500
TIMELINE_FIG_WIDTH = 14
TIMELINE_FIG_HEIGHT_PER_ACTIVITY = 0.3
NETWORK_FIG_SIZE = (14, 10)
LABEL_MAX_CHARS = 30
DESC_DISPLAY_MAX = 60
DESC_DATA_MAX = 300
SANITIZE_LABEL_MAX = 50
MITRE_TOP_TECHNIQUES = 20
NODE_SIZE_VIS = 40
DPI_SAVE = 150
DEFAULT_ICON = "unknown.png"


def _get_icon_mapping_from_yaml() -> Dict[str, str]:
    """Build normalized system type -> icon_filename from system_types.yaml."""
    mapping = {}
    for t in _load_system_types_from_yaml():
        name = t.get("name", "")
        icon = t.get("icon_filename")
        if name and icon:
            key = name.lower().strip()
            mapping[key] = icon.strip()
    return mapping


def _infer_icon_from_label_fallback(label: str) -> str:
    """Last-resort heuristic when no DB/YAML match. Uses system_types.yaml structure only."""
    if not label:
        return DEFAULT_ICON
    lower = label.lower().strip()
    yaml_mapping = _get_icon_mapping_from_yaml()
    for key, icon in yaml_mapping.items():
        if key in lower or lower in key:
            return icon
    if "domain" in lower or "dc" in lower:
        return yaml_mapping.get("server-dc", DEFAULT_ICON)
    if "firewall" in lower or "palo" in lower or "sonicwall" in lower:
        return yaml_mapping.get("gateway-firewall", DEFAULT_ICON)
    if "server" in lower:
        return yaml_mapping.get("server-generic", DEFAULT_ICON)
    return DEFAULT_ICON


def normalize_system_type(st: str) -> str:
    if not st:
        return ""
    return str(st).strip().lower()


def images_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "images"


def icon_to_data_url(icon_filename: str, cache: Optional[Dict[str, str]] = None) -> Optional[str]:
    cache = cache if cache is not None else {}
    if icon_filename in cache:
        return cache[icon_filename]
    requested = icon_filename
    img_dir = images_dir()
    path = img_dir / icon_filename
    if not path.is_file():
        fallback = img_dir / DEFAULT_ICON
        path = fallback if fallback.is_file() else None
        if path is None:
            cache[requested] = None
            return None
        icon_filename = DEFAULT_ICON
        path = img_dir / icon_filename
    try:
        raw = path.read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        ext = "png" if icon_filename.lower().endswith(".png") else "jpeg"
        data_url = f"data:image/{ext};base64,{b64}"
        cache[icon_filename] = data_url
        cache[requested] = data_url
        return data_url
    except Exception as e:
        logger.warning("Could not load icon %s: %s", icon_filename, e)
        cache[requested] = None
        return None


class VisualizationGenerator:

    def __init__(self, workbook, output_dir: Optional[str] = None, db_path: Optional[str] = None):
        self.workbook = workbook
        self.output_dir = output_dir or tempfile.mkdtemp()
        self.db_path = db_path or ""
        self.generated_images = {}
        self.icon_cache: Dict[str, str] = {}
        self._icon_mapping: Optional[Dict[str, str]] = None

    def _get_icon_mapping(self) -> Dict[str, str]:
        """Load icon mapping from DB if available, else from system_types.yaml."""
        if self._icon_mapping is not None:
            return self._icon_mapping
        if self.db_path:
            self._icon_mapping = load_icon_mapping_from_db(self.db_path)
        if not self._icon_mapping:
            self._icon_mapping = _get_icon_mapping_from_yaml()
        return self._icon_mapping

    def generate_timeline_image(self, sheet_name: Optional[str] = None) -> Optional[str]:
        sheet_name = sheet_name or config.SHEET_TIMELINE
        try:
            if sheet_name not in self.workbook.sheetnames:
                logger.warning("Sheet '%s' not found for timeline visualization", sheet_name)
                return None
            sheet = self.workbook[sheet_name]
            headers = [cell.value for cell in sheet[1]]
            headers = [str(h) if h else "Column %s" % (i + 1) for i, h in enumerate(headers)]
            try:
                dt_col = headers.index(config.COL_TIMESTAMP)
                desc_col = headers.index(config.COL_ACTIVITY)
                mitre_col = headers.index(config.COL_MITRE_TACTIC)
            except ValueError:
                logger.warning("Required columns not found for timeline visualization")
                return None
            activities = []
            for row_idx in range(2, min(sheet.max_row + 1, MAX_TIMELINE_ROWS)):
                try:
                    dt_val = sheet.cell(row=row_idx, column=dt_col+1).value
                    desc_val = sheet.cell(row=row_idx, column=desc_col+1).value
                    mitre_val = sheet.cell(row=row_idx, column=mitre_col+1).value
                    
                    if not (dt_val and desc_val and mitre_val):
                        continue
                    
                    if isinstance(dt_val, datetime):
                        activity_datetime = dt_val
                    elif isinstance(dt_val, str):
                        try:
                            activity_datetime = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                activity_datetime = datetime.strptime(dt_val, "%Y-%m-%d")
                            except ValueError:
                                continue
                    else:
                        continue
                    
                    activities.append((activity_datetime, str(desc_val), str(mitre_val)))
                except Exception:
                    continue
            
            if not activities:
                logger.warning("No timeline activities found")
                return None
            activities.sort(key=lambda x: x[0])
            fig_height = max(8, len(activities) * TIMELINE_FIG_HEIGHT_PER_ACTIVITY)
            fig, ax = plt.subplots(figsize=(TIMELINE_FIG_WIDTH, fig_height))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            min_date = activities[0][0]
            max_date = activities[-1][0]
            time_range = (max_date - min_date).total_seconds()
            if time_range == 0:
                time_range = 1
            line_x = 0.1
            ax.axvline(x=line_x, ymin=0, ymax=1, color='black', linewidth=2)
            y_positions = []
            for i, (dt, desc, mitre) in enumerate(activities):
                y_pos = 1.0 - (i / len(activities)) * 0.9
                y_positions.append(y_pos)
                ax.plot(line_x, y_pos, 'o', color='blue', markersize=8)
                timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                ax.text(line_x - 0.05, y_pos, timestamp_str, 
                       fontsize=8, ha='right', va='center', color='red', weight='bold',
                       family='sans-serif')
                mitre_clean = str(mitre).replace("\t", " ").replace("\n", " ").replace("\r", " ")[:LABEL_MAX_CHARS]
                ax.add_patch(plt.Rectangle((line_x + 0.01, y_pos - 0.01), 0.3, 0.02,
                                          facecolor='darkorange', edgecolor='none'))
                ax.text(line_x + 0.16, y_pos, mitre_clean, fontsize=8, ha='center', 
                       va='center', color='white', weight='bold', family='sans-serif')
                desc_short = (desc[:DESC_DISPLAY_MAX] + "...") if len(desc) > DESC_DISPLAY_MAX else desc
                desc_short = desc_short.replace("\t", " ").replace("\n", " ").replace("\r", " ")
                ax.text(line_x + 0.32, y_pos, desc_short, fontsize=8, ha='left', va='center', 
                       family='sans-serif')
            
            ax.set_xlim(-0.1, 1.0)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.set_title('Timeline Visualization', fontsize=14, weight='bold', pad=20, family='sans-serif')
            plt.tight_layout()
            buf = BytesIO()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                plt.savefig(buf, format="png", dpi=DPI_SAVE, bbox_inches="tight", facecolor="white")
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode("utf-8")
            plt.close(fig)
            return "data:image/png;base64,%s" % img_base64
        except Exception as e:
            logger.error("Error generating timeline image: %s", e)
            return None

    def get_timeline_data(self, sheet_name: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        sheet_name = sheet_name or config.SHEET_TIMELINE
        try:
            if sheet_name not in self.workbook.sheetnames:
                logger.warning("Sheet '%s' not found for timeline data", sheet_name)
                return None
            sheet = self.workbook[sheet_name]
            headers = [cell.value for cell in sheet[1]]
            headers = [str(h) if h else "Column %s" % (i + 1) for i, h in enumerate(headers)]
            try:
                dt_col = headers.index(config.COL_TIMESTAMP)
                desc_col = headers.index(config.COL_ACTIVITY)
                mitre_col = headers.index(config.COL_MITRE_TACTIC)
            except ValueError:
                logger.warning("Required columns not found for timeline data")
                return None
            events: List[Dict[str, Any]] = []
            for row_idx in range(2, min(sheet.max_row + 1, MAX_TIMELINE_ROWS)):
                try:
                    dt_val = sheet.cell(row=row_idx, column=dt_col + 1).value
                    desc_val = sheet.cell(row=row_idx, column=desc_col + 1).value
                    mitre_val = sheet.cell(row=row_idx, column=mitre_col + 1).value
                    
                    if not (dt_val and desc_val and mitre_val):
                        continue
                    if isinstance(dt_val, datetime):
                        activity_datetime = dt_val
                    elif isinstance(dt_val, str):
                        try:
                            activity_datetime = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                activity_datetime = datetime.strptime(dt_val, "%Y-%m-%d")
                            except ValueError:
                                continue
                    else:
                        continue
                    desc_str = str(desc_val).replace("\t", " ").replace("\n", " ").replace("\r", " ")
                    mitre_str = str(mitre_val).replace("\t", " ").replace("\n", " ").replace("\r", " ")
                    short_desc = desc_str if len(desc_str) <= DESC_DATA_MAX else desc_str[:DESC_DATA_MAX - 3] + "..."
                    
                    events.append(
                        {
                            "timestamp": activity_datetime.isoformat(),
                            "timestamp_display": activity_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                            "activity": short_desc,
                            "mitre_tactic": mitre_str,
                        }
                    )
                except Exception:
                    continue
            if not events:
                return None
            events.sort(key=lambda e: e["timestamp"])
            return events
        except Exception as e:
            logger.error("Error building timeline data: %s", e)
            return None

    def generate_network_image(self, sheet_name: Optional[str] = None) -> Optional[str]:
        sheet_name = sheet_name or config.SHEET_TIMELINE
        try:
            if sheet_name not in self.workbook.sheetnames:
                logger.warning("Sheet '%s' not found for network visualization", sheet_name)
                return None
            sheet = self.workbook[sheet_name]
            headers = [cell.value for cell in sheet[1]]
            headers = [str(h) if h else "Column %s" % (i + 1) for i, h in enumerate(headers)]
            required_columns = [config.COL_EVENT_SYSTEM, config.COL_REMOTE_SYSTEM, config.COL_DIRECTION, config.COL_VISUALIZE]
            column_indices = {}
            for col_name in required_columns:
                if col_name in headers:
                    column_indices[col_name] = headers.index(col_name)
                else:
                    logger.warning("Column '%s' not found for network visualization", col_name)
                    return None
            G = nx.DiGraph()
            for row_idx in range(2, min(sheet.max_row + 1, MAX_NETWORK_ROWS)):
                try:
                    visualize_val = sheet.cell(row=row_idx, column=column_indices[config.COL_VISUALIZE] + 1).value
                    if str(visualize_val).lower() != config.VAL_VISUALIZE_YES:
                        continue
                    event_system = sheet.cell(row=row_idx, column=column_indices[config.COL_EVENT_SYSTEM] + 1).value
                    remote_system = sheet.cell(row=row_idx, column=column_indices[config.COL_REMOTE_SYSTEM] + 1).value
                    direction = sheet.cell(row=row_idx, column=column_indices[config.COL_DIRECTION] + 1).value
                    
                    if not (event_system and remote_system and direction):
                        continue
                    
                    event_system = str(event_system).strip()
                    remote_system = str(remote_system).strip()
                    direction = str(direction).strip()
                    
                    G.add_node(event_system)
                    G.add_node(remote_system)
                    
                    if direction == "->":
                        G.add_edge(event_system, remote_system)
                    elif direction == "<-":
                        G.add_edge(remote_system, event_system)
                    elif direction == "<->":
                        G.add_edge(event_system, remote_system)
                        G.add_edge(remote_system, event_system)
                except Exception:
                    continue
            
            if not G.nodes():
                logger.warning("No network nodes found")
                return None
            fig, ax = plt.subplots(figsize=NETWORK_FIG_SIZE)
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")
            pos = nx.spring_layout(G, k=1, iterations=50, seed=42)
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color="lightblue",
                                  node_size=1000, alpha=0.9, edgecolors="black", linewidths=2)
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color="gray",
                                  arrows=True, arrowsize=20, alpha=0.6, width=1.5)
            labels = {node: str(node).replace("\t", " ").replace("\n", " ").replace("\r", " ")[:LABEL_MAX_CHARS]
                      for node in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=8, font_weight='bold', 
                                   font_family='sans-serif')
            
            ax.set_title('Network Visualization', fontsize=14, weight='bold', pad=20, family='sans-serif')
            ax.axis('off')
            plt.tight_layout()
            buf = BytesIO()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                plt.savefig(buf, format="png", dpi=DPI_SAVE, bbox_inches="tight", facecolor="white")
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode("utf-8")
            plt.close(fig)
            return "data:image/png;base64,%s" % img_base64
        except Exception as e:
            logger.error("Error generating network image: %s", e)
            return None

    def get_network_data(self, sheet_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        sheet_name = sheet_name or config.SHEET_TIMELINE
        try:
            if sheet_name not in self.workbook.sheetnames:
                return None
            sheet = self.workbook[sheet_name]
            headers = [cell.value for cell in sheet[1]]
            headers = [str(h) if h else "Column %s" % (i + 1) for i, h in enumerate(headers)]
            required_columns = [config.COL_EVENT_SYSTEM, config.COL_REMOTE_SYSTEM, config.COL_DIRECTION, config.COL_VISUALIZE]
            column_indices = {}
            for col_name in required_columns:
                if col_name in headers:
                    column_indices[col_name] = headers.index(col_name)
                else:
                    return None
            G = nx.DiGraph()
            for row_idx in range(2, min(sheet.max_row + 1, MAX_NETWORK_ROWS)):
                try:
                    visualize_val = sheet.cell(row=row_idx, column=column_indices[config.COL_VISUALIZE] + 1).value
                    if str(visualize_val).lower() != config.VAL_VISUALIZE_YES:
                        continue
                    event_system = sheet.cell(row=row_idx, column=column_indices[config.COL_EVENT_SYSTEM] + 1).value
                    remote_system = sheet.cell(row=row_idx, column=column_indices[config.COL_REMOTE_SYSTEM] + 1).value
                    direction = sheet.cell(row=row_idx, column=column_indices[config.COL_DIRECTION] + 1).value
                    if not (event_system and remote_system and direction):
                        continue
                    event_system = str(event_system).strip()
                    remote_system = str(remote_system).strip()
                    direction = str(direction).strip()
                    G.add_node(event_system)
                    G.add_node(remote_system)
                    if direction == "->":
                        G.add_edge(event_system, remote_system)
                    elif direction == "<-":
                        G.add_edge(remote_system, event_system)
                    elif direction == "<->":
                        G.add_edge(event_system, remote_system)
                        G.add_edge(remote_system, event_system)
                except Exception:
                    continue
            if not G.nodes():
                return None
            hostname_to_system_type: Dict[str, str] = {}
            try:
                if config.SHEET_SYSTEMS in self.workbook.sheetnames:
                    sys_sheet = self.workbook[config.SHEET_SYSTEMS]
                    sys_headers = [cell.value for cell in sys_sheet[1]]
                    sys_headers = [str(h) if h else "" for h in sys_headers]
                    if config.COL_HOSTNAME in sys_headers and config.COL_SYSTEM_TYPE in sys_headers:
                        host_col = sys_headers.index(config.COL_HOSTNAME) + 1
                        type_col = sys_headers.index(config.COL_SYSTEM_TYPE) + 1
                        for r in range(2, min(sys_sheet.max_row + 1, 500)):
                            host = sys_sheet.cell(row=r, column=host_col).value
                            st = sys_sheet.cell(row=r, column=type_col).value
                            if host and st:
                                hostname_to_system_type[str(host).strip()] = str(st).strip()
            except Exception as e:
                logger.debug("Could not read Systems sheet for icons: %s", e)

            icon_mapping = self._get_icon_mapping()

            def icon_filename_for_node(node_id: str) -> str:
                st = hostname_to_system_type.get(node_id)
                if st:
                    key = normalize_system_type(st)
                    if key in icon_mapping:
                        return icon_mapping[key]
                    for map_key, icon in icon_mapping.items():
                        if key in map_key or map_key in key:
                            return icon
                return _infer_icon_from_label_fallback(node_id)
            
            def sanitize(s: str) -> str:
                return str(s).replace("\t", " ").replace("\n", " ").replace("\r", " ")[:SANITIZE_LABEL_MAX]

            nodes = []
            for n in G.nodes():
                icon_file = icon_filename_for_node(n)
                image_url = icon_to_data_url(icon_file, self.icon_cache)
                node_entry = {
                    "id": n,
                    "label": sanitize(n),
                    "title": sanitize(n),
                }
                if image_url:
                    node_entry["shape"] = "image"
                    node_entry["image"] = image_url
                    node_entry["size"] = NODE_SIZE_VIS
                    node_entry["brokenImage"] = None
                nodes.append(node_entry)
            edges = [{"from": u, "to": v, "arrows": "to"} for u, v in G.edges()]
            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.warning("Could not get network data for vis.js: %s", e)
            return None

    def generate_mitre_statistics(self, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        sheet_name = sheet_name or config.SHEET_TIMELINE
        try:
            if sheet_name not in self.workbook.sheetnames:
                return {}
            sheet = self.workbook[sheet_name]
            headers = [cell.value for cell in sheet[1]]
            headers = [str(h) if h else "Column %s" % (i + 1) for i, h in enumerate(headers)]
            if config.COL_MITRE_TACTIC not in headers:
                return {}
            mitre_tactic_index = headers.index(config.COL_MITRE_TACTIC)
            mitre_techniques_index = headers.index(config.COL_MITRE_TECHNIQUE) if config.COL_MITRE_TECHNIQUE in headers else None
            tactics_count = {}
            techniques_count = {}
            tactics_techniques = {}
            for row_idx in range(2, sheet.max_row + 1):
                tactic_value = sheet.cell(row=row_idx, column=mitre_tactic_index + 1).value
                if tactic_value and str(tactic_value).strip():
                    tactic = str(tactic_value).strip()
                    tactics_count[tactic] = tactics_count.get(tactic, 0) + 1
                    if tactic not in tactics_techniques:
                        tactics_techniques[tactic] = []
                    if mitre_techniques_index is not None:
                        technique = sheet.cell(row=row_idx, column=mitre_techniques_index + 1).value
                        if technique and str(technique).strip():
                            technique = str(technique).strip()
                            techniques_count[technique] = techniques_count.get(technique, 0) + 1
                            if technique not in tactics_techniques[tactic]:
                                tactics_techniques[tactic].append(technique)
            total_detections = sum(len(techniques) for techniques in tactics_techniques.values())
            return {
                "total_detections": total_detections,
                "unique_tactics": len(tactics_count),
                "unique_techniques": len(techniques_count),
                "tactics_count": dict(sorted(tactics_count.items(), key=lambda x: x[1], reverse=True)),
                "techniques_count": dict(sorted(techniques_count.items(), key=lambda x: x[1], reverse=True)[:MITRE_TOP_TECHNIQUES]),
                "tactics_techniques": tactics_techniques,
            }
        except Exception as e:
            logger.error("Error generating MITRE statistics: %s", e)
            return {}

