"""
HTML report exporter for Kanvas: builds detailed HTML reports from workbook data,
optional timeline/network visualizations, recommendations, and investigation
summary. Cross-platform (Windows, macOS, Linux). Revised on 01/02/2026 by Jinto Antony
"""

import base64
import html as html_module
import json
import logging
import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import markdown
import openpyxl
import pandas as pd
from markdown.extensions import codehilite, fenced_code, tables

from helper import config
from helper.defang import defang_text
from helper.reporting.visualization_generator import VisualizationGenerator

logger = logging.getLogger(__name__)

SHEET_DISPLAY_NAMES = {
    config.SHEET_ACCOUNTS: "Compromised Accounts",
    config.SHEET_SYSTEMS: "Compromised Systems",
    config.SHEET_INDICATORS: "IOC (Indicators of Compromise)",
    "VERIS": "VERIS (Vocabulary for Event Recording and Incident Sharing)",
}
IOC_DEFANG_TYPES = frozenset(("ipaddress", "url", "domainname", "emailaddress"))


def _lighten_hex(hex_color: str, mix_white: float = 0.88) -> str:
    """Return a lighter tint of hex_color by mixing with white (0 = original, 1 = white)."""
    hex_color = (hex_color or "#235AAA").strip().lstrip("#")
    if len(hex_color) != 6:
        return "#E8EEF7"
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r + (255 - r) * mix_white)
        g = int(g + (255 - g) * mix_white)
        b = int(b + (255 - b) * mix_white)
        return "#%02x%02x%02x" % (r, g, b)
    except (ValueError, TypeError):
        return "#E8EEF7"


class HTMLExporter:

    def get_sheet_display_name(self, sheet_name: str) -> str:
        sheet_lower = sheet_name.lower()
        for key, display_name in SHEET_DISPLAY_NAMES.items():
            if sheet_lower == key.lower():
                return display_name
        return sheet_name

    def summary_text_to_html(self, text: str) -> str:
        if not text or not text.strip():
            return "<p>No summary provided.</p>"
        escaped = html_module.escape(text)
        lines = escaped.splitlines()
        out = []
        in_list = False
        paragraph_lines = []

        def flush_paragraph():
            nonlocal paragraph_lines
            if paragraph_lines:
                para = '<br>\n'.join(paragraph_lines)
                out.append(f'<p>{para}</p>')
                paragraph_lines.clear()

        def flush_list():
            nonlocal in_list
            if in_list:
                out.append('</ul>')
                in_list = False

        def is_bullet_line(stripped: str) -> bool:
            if not stripped:
                return False
            if stripped.startswith('- ') or stripped.startswith('* '):
                return True
            if stripped.startswith('•') or stripped.startswith('◦'):
                return True
            if len(stripped) >= 2 and stripped[0].isdigit() and stripped[1] == '.':
                return True
            return False

        def bullet_content(stripped: str) -> str:
            if stripped.startswith('- ') or stripped.startswith('* '):
                return stripped[2:].strip()
            if stripped.startswith('•') or stripped.startswith('◦'):
                return stripped[1:].strip()
            if len(stripped) >= 2 and stripped[0].isdigit() and stripped[1] == '.':
                i = 2
                while i < len(stripped) and stripped[i] in ' \t':
                    i += 1
                return stripped[i:].strip() if i < len(stripped) else ''
            return stripped

        for line in lines:
            stripped = line.strip()
            if not stripped:
                flush_list()
                flush_paragraph()
                continue
            if is_bullet_line(stripped):
                flush_paragraph()
                if not in_list:
                    out.append('<ul>')
                    in_list = True
                content = bullet_content(stripped)
                out.append(f'<li>{content}</li>')
            else:
                flush_list()
                paragraph_lines.append(stripped)
        flush_list()
        flush_paragraph()
        return '\n'.join(out) if out else '<p>No summary provided.</p>'

    def strip_markdown_section(self, content: str, heading_text: str, include_subsections: bool = True) -> str:
        if not content or not content.strip():
            return content
        heading_lower = heading_text.strip().lower()
        lines = content.split('\n')
        result = []
        in_section = False
        target_level = None  
        heading_pattern = re.compile(r'^(#+)\s+(.+)$')
        for line in lines:
            m = heading_pattern.match(line.strip())
            if m:
                current_level = len(m.group(1))
                current_heading = m.group(2).strip().lower()
                if current_heading == heading_lower:
                    in_section = True
                    target_level = current_level
                    continue
                elif in_section:
                    if include_subsections:
                        if current_level <= target_level:
                            in_section = False
                    else:
                        in_section = False
            if not in_section:
                result.append(line)
        return '\n'.join(result).strip()

    def parse_diamond_model_section(self, content: str) -> Optional[List[Tuple[str, str]]]:
        if not content or not content.strip():
            return None
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        in_section = False
        facets: List[Tuple[str, str]] = []
        current_title = None
        current_lines: List[str] = []
        heading_pattern = re.compile(r'^(#+)\s+(.+)$')

        for line in lines:
            m = heading_pattern.match(line.strip())
            if m:
                level = len(m.group(1))
                heading_text = m.group(2).strip()
                if level <= 2 and heading_text.lower() == 'diamond model':
                    in_section = True
                    continue
                if in_section and level == 1:
                    break
                if in_section and level == 3:
                    if current_title is not None:
                        body = '\n'.join(current_lines).strip()
                        if current_title or body:
                            facets.append((current_title, body))
                        if len(facets) >= 4:
                            break
                    current_title = heading_text
                    current_lines = []
                    continue
            if in_section:
                if current_title is not None:
                    current_lines.append(line)

        if current_title is not None:
            body = '\n'.join(current_lines).strip()
            if current_title or body:
                facets.append((current_title, body))

        return facets if facets else None

    def build_diamond_model_html(
        self,
        facets: List[Tuple[str, str]],
        report_color: str,
        source_file_path: Optional[str] = None,
    ) -> str:
        if not facets:
            return ""
        accent_esc = html_module.escape(report_color)
        center_html: str
        diamond_path = None
        if source_file_path:
            source_dir = Path(source_file_path).resolve().parent
            candidate = source_dir / "images" / "diamond.jpg"
            if candidate.is_file():
                diamond_path = candidate
        if diamond_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            candidate = project_root / "images" / "diamond.jpg"
            if candidate.is_file():
                diamond_path = candidate
        if diamond_path:
            try:
                img_b64 = base64.b64encode(diamond_path.read_bytes()).decode("ascii")
                center_html = (
                    '<div class="diamond-model-center diamond-model-center--image">'
                    f'<img src="data:image/jpeg;base64,{img_b64}" alt="Diamond" />'
                    '</div>'
                )
            except Exception as e:
                logger.warning("Could not load diamond.jpg for Diamond Model: %s", e)
                center_html = '<div class="diamond-model-center" style="border-color: %s;"></div>' % accent_esc
        else:
            center_html = '<div class="diamond-model-center" style="border-color: %s;"></div>' % accent_esc
        positions = ['top', 'left', 'right', 'bottom']
        parts = []
        for i, (title, body) in enumerate(facets[:4]):
            pos = positions[i]
            body_html = self.convert_markdown_to_html(body.strip(), source_file_path) if body.strip() else ""
            title_esc = html_module.escape(title)
            parts.append(
                f'<div class="diamond-facet diamond-facet-{pos}">'
                f'<div class="diamond-facet-title">{title_esc}</div>'
                f'<div class="diamond-facet-content">{body_html}</div>'
                f'</div>'
            )
        return (
            f'<div class="diamond-model-section">'
            + center_html
            + ''.join(parts) +
            '</div>'
        )

    def convert_markdown_to_html(self, markdown_content: str, source_file_path: str = None) -> str:
        try:
            html_content = markdown.markdown(
                markdown_content,
                extensions=['fenced_code', 'tables', 'codehilite', 'nl2br']
            )
            
            def replace_meta_paragraph(match):
                label = match.group(1).strip()
                value = match.group(2).strip()
                label_esc = html_module.escape(label)
                value_esc = html_module.escape(value)
                slug = value.lower().replace(' ', '-').replace('_', '-') if value else 'value'
                slug = re.sub(r'[^a-z0-9-]', '', slug) or 'value'
                extra_class = ''
                if label.lower() == 'criticality' and value:
                    extra_class = f' recommendation-criticality-{slug}'
                return (
                    f'<div class="recommendation-meta">'
                    f'<span class="recommendation-meta-label">{label_esc}:</span> '
                    f'<span class="recommendation-meta-value{extra_class}">{value_esc}</span>'
                    f'</div>'
                )
            html_content = re.sub(
                r'<p>\s*<strong>([^<]+):</strong>\s*([^<]*)</p>',
                replace_meta_paragraph,
                html_content
            )
            if source_file_path:
                source_dir = Path(source_file_path).resolve().parent
                def replace_image(match):
                    alt_text = match.group(1)
                    img_path = match.group(2)
                    if img_path.startswith(("http://", "https://")):
                        return match.group(0)
                    path = Path(img_path)
                    if not path.is_absolute():
                        abs_path = (source_dir / img_path).resolve()
                    else:
                        abs_path = Path(img_path)
                    if abs_path.is_file():
                        try:
                            img_data = base64.b64encode(abs_path.read_bytes()).decode("utf-8")
                            ext = abs_path.suffix.lower()
                            mime_type = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/gif" if ext == ".gif" else "image/png"
                            return '<img src="data:%s;base64,%s" alt="%s" />' % (mime_type, img_data, alt_text)
                        except Exception as e:
                            logger.warning("Could not embed image %s: %s", abs_path, e)
                            return '<img src="file:///%s" alt="%s" />' % (abs_path.as_posix(), alt_text)
                    logger.warning("Image file not found: %s", abs_path)
                    return "<p><em>Image not found: %s</em></p>" % img_path
                html_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, html_content)
                def replace_img_src(match):
                    quote = match.group(1)
                    src = match.group(2).strip()
                    if src.startswith(("http://", "https://", "data:")):
                        return match.group(0)
                    path = Path(src)
                    if not path.is_absolute():
                        abs_path = (source_dir / src).resolve()
                    else:
                        abs_path = Path(src)
                    if not abs_path.is_file():
                        logger.warning("Image file not found for embed: %s", abs_path)
                        return match.group(0)
                    try:
                        img_data = base64.b64encode(abs_path.read_bytes()).decode("utf-8")
                        ext = abs_path.suffix.lower()
                        mime = "image/png" if ext == ".png" else "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/gif" if ext == ".gif" else "image/webp" if ext == ".webp" else "image/png"
                        return "src=%sdata:%s;base64,%s%s" % (quote, mime, img_data, quote)
                    except Exception as e:
                        logger.warning("Could not embed image as base64: %s - %s", abs_path, e)
                        return match.group(0)
                html_content = re.sub(r'src=(["\'])([^"\']+)\1', replace_img_src, html_content)
            
            return html_content
            
        except ImportError:
            logger.warning("markdown library not available, using basic formatting")
            html_content = markdown_content.replace('\n', '<br>')
            return f"<div>{html_content}</div>"
        except Exception as e:
            logger.warning("Error converting markdown to HTML: %s", e)
            return "<pre>%s</pre>" % markdown_content
    
    def sort_recommendations_by_criticality(self, markdown_content: str) -> str:
        if not markdown_content or not markdown_content.strip():
            return markdown_content
        criticality_order = ("critical", "high", "medium", "low", "info")
        parts = re.split(r'\n(?=^##\s+)', markdown_content.strip(), flags=re.MULTILINE)
        intro = []
        sections = []
        for part in parts:
            part = part.rstrip()
            if not part:
                continue
            if not part.startswith('## '):
                intro.append(part)
                continue
            match = re.search(r'\*\*Criticality:\*\*\s*(\S+)', part, re.IGNORECASE)
            value = (match.group(1).strip().rstrip('.,;').lower() if match else "")
            sort_key = criticality_order.index(value) if value in criticality_order else len(criticality_order)
            sections.append((sort_key, part))
        sections.sort(key=lambda x: x[0])
        result = '\n\n'.join(intro) if intro else ""
        if result:
            result += '\n\n'
        result += '\n\n'.join(p[1] for p in sections)
        return result.strip()
    
    def export(self, report_data: Dict[str, Any], output_path: str, template: str = "detailed") -> bool:
        try:
            workbook = report_data.get("workbook")
            if not workbook:
                excel_file = report_data.get("excel_file_name")
                excel_path = Path(excel_file) if excel_file else None
                if excel_path and excel_path.is_file():
                    try:
                        workbook = openpyxl.load_workbook(str(excel_path), read_only=True)
                    except Exception as e:
                        logger.warning("Could not load workbook for visualizations: %s", e)
                        workbook = None
            template_type = report_data.get("html_template", template)
            html_content = self.build_html(report_data, workbook, template_type)
            output_path_obj = Path(output_path)
            output_dir = output_path_obj.parent
            if output_dir and not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            output_path_obj.write_text(html_content, encoding="utf-8")
            logger.info("HTML report exported successfully to %s", output_path)
            return True
        except Exception as e:
            logger.exception("Error exporting to HTML: %s", e)
            return False
    
    def build_html(self, report_data: Dict[str, Any], workbook=None, template: str = "detailed") -> str:
        return self.build_detailed_html(report_data, workbook)

    def build_detailed_html(self, report_data: Dict[str, Any], workbook=None) -> str:
        title = report_data.get("title", "KANVAS Report")
        author = report_data.get("author", "KANVAS User")
        title_esc = html_module.escape(title)
        author_esc = html_module.escape(author)
        summary_raw = report_data.get("summary", "No summary provided.")
        investigation_summary_file_path = report_data.get("investigation_summary_file_path")
        if summary_raw and summary_raw.strip() and summary_raw.strip() != "No summary provided.":
            summary_for_html = defang_text(summary_raw.strip())
            summary_html = self.convert_markdown_to_html(
                summary_for_html, investigation_summary_file_path
            )
        else:
            summary_html = self.summary_text_to_html(summary_raw or "No summary provided.")
        excel_file_name = report_data.get("excel_file_name", "N/A")
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        images_constrained = report_data.get("images_constrained", True)
        report_full_width = report_data.get("report_full_width", False)
        header_options = report_data.get("header_options") or {}
        footer_options = report_data.get("footer_options") or {}
        report_font = report_data.get("report_font", "Inter")
        report_color = report_data.get("report_color", "#235AAA")
        report_color_tag_bg = _lighten_hex(report_color)
        enable_visualizations = report_data.get("enable_visualizations", True)
        selected_sections: Dict[str, bool] = report_data.get("selected_sections", {}) or {}
        container_class = "report-container"
        if not images_constrained:
            container_class += " images-full-size"
        if report_full_width:
            container_class += " report-full-width"
        
        if report_font == "Inter":
            font_link = '<link rel="preconnect" href="https://fonts.googleapis.com">\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
            font_family = "'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
        else:
            font_link = ""
            font_stacks = {
                "Arial": "'Arial', Helvetica, sans-serif",
                "Georgia": "'Georgia', 'Times New Roman', serif",
                "Segoe UI": "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
                "Times New Roman": "'Times New Roman', Times, serif",
                "Verdana": "Verdana, Geneva, sans-serif",
            }
            font_family = font_stacks.get(report_font, "'%s', sans-serif" % report_font)
        if header_options.get("include_headers", True):
            meta_items = []
            if header_options.get("author", True):
                meta_items.append(f'<div class="header-meta-item"><strong>Author:</strong> {author_esc}</div>')
            if header_options.get("generated", True):
                meta_items.append(f'<div class="header-meta-item"><strong>Generated:</strong> {timestamp}</div>')
            if header_options.get("source", True):
                source_text = Path(excel_file_name).name if excel_file_name and excel_file_name != "N/A" else "N/A"
                meta_items.append(f'<div class="header-meta-item"><strong>Source:</strong> {source_text}</div>')
            conf = (header_options.get("confidentiality") or "").strip()
            if conf:
                meta_items.append(f'<div class="header-meta-item"><strong>Confidentiality:</strong> {conf}</div>')
            if header_options.get("reviewed_by", True):
                rev_text = (header_options.get("reviewed_by_text") or "").strip()
                if rev_text:
                    meta_items.append(f'<div class="header-meta-item"><strong>Reviewed by:</strong> {html_module.escape(rev_text)}</div>')
            if header_options.get("case_id", True):
                case_text = (header_options.get("case_id_text") or "").strip()
                if case_text:
                    meta_items.append(f'<div class="header-meta-item"><strong>Case ID:</strong> {html_module.escape(case_text)}</div>')
            meta_html = "\n                ".join(meta_items) if meta_items else ""
            header_html = f"""
        <div class="header">
            <h1>{title_esc}</h1>
            <div class="header-meta">
                {meta_html}
            </div>
        </div>

        """
        else:
            header_html = ""
        
        if footer_options.get("include_footers", True):
            footer_lines = []
            if footer_options.get("report_generated_on", True):
                footer_lines.append(f'<p>Report generated on {timestamp}</p>')
            if footer_options.get("contact", True):
                contact_text = (footer_options.get("contact_text") or "").strip() or author
                footer_lines.append(f'<p>For questions or issues, please contact: {html_module.escape(contact_text)}</p>')
            if footer_options.get("contact_number", True):
                contact_num_text = (footer_options.get("contact_number_text") or "").strip()
                if contact_num_text:
                    footer_lines.append(f'<p><strong>Contact Number:</strong> {html_module.escape(contact_num_text)}</p>')
            if footer_options.get("website", True):
                website_text = (footer_options.get("website_text") or "").strip()
                if website_text:
                    footer_lines.append(f'<p><strong>Website:</strong> <a href="{html_module.escape(website_text)}">{html_module.escape(website_text)}</a></p>')
            if footer_options.get("reviewed_by", True):
                rev_text = (footer_options.get("reviewed_by_text") or "").strip()
                if rev_text:
                    footer_lines.append(f'<p><strong>Reviewed by:</strong> {html_module.escape(rev_text)}</p>')
            if footer_options.get("case_id", True):
                case_text = (footer_options.get("case_id_text") or "").strip()
                if case_text:
                    footer_lines.append(f'<p><strong>Case ID:</strong> {html_module.escape(case_text)}</p>')
            footer_inner = "\n            ".join(footer_lines) if footer_lines else ""
            footer_html = f"""
        <div class="footer">
            {footer_inner}
        </div>
"""
        else:
            footer_html = ""
        
        def section_enabled(label: str) -> bool:
            return selected_sections.get(label, True) if selected_sections else True

        show_timeline_section = enable_visualizations and section_enabled("Incident Timeline")
        show_lateral_section = enable_visualizations and section_enabled("Lateral Movement")
        show_mitre_section = enable_visualizations and section_enabled("MITRE ATT&CK Tactics & Techniques Mapping")

        timeline_img = None
        network_img = None
        network_data = None
        timeline_data = None
        mitre_stats = {}
        recommendations_content = None
        timeline_image_path = report_data.get("timeline_image_path")
        network_image_path = report_data.get("network_image_path")
        recommendations_file_path = report_data.get("recommendations_file_path")
        timeline_path = Path(timeline_image_path) if timeline_image_path else None
        if timeline_path and timeline_path.is_file():
            try:
                img_data = base64.b64encode(timeline_path.read_bytes()).decode("utf-8")
                ext = timeline_path.suffix.lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                timeline_img = "data:%s;base64,%s" % (mime_type, img_data)
                logger.info("Loaded timeline image from: %s", timeline_image_path)
            except Exception as e:
                logger.warning("Could not load timeline image: %s", e)
        network_path = Path(network_image_path) if network_image_path else None
        if network_path and network_path.is_file():
            try:
                img_data = base64.b64encode(network_path.read_bytes()).decode("utf-8")
                ext = network_path.suffix.lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                network_img = "data:%s;base64,%s" % (mime_type, img_data)
                logger.info("Loaded network image from: %s", network_image_path)
            except Exception as e:
                logger.warning("Could not load network image: %s", e)
        if enable_visualizations and workbook:
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    db_path = report_data.get("db_path", "") or ""
                    viz_gen = VisualizationGenerator(workbook, db_path=db_path)
                    if not timeline_img:
                        try:
                            timeline_img = viz_gen.generate_timeline_image()
                        except Exception as e:
                            logger.warning("Could not generate timeline image: %s", e)
                    if not network_img:
                        try:
                            network_img = viz_gen.generate_network_image()
                        except Exception as e:
                            logger.warning("Could not generate network image: %s", e)
                    try:
                        network_data = viz_gen.get_network_data()
                    except Exception as e:
                        logger.warning("Could not get network data for interactive viz: %s", e)
                        network_data = None
                    try:
                        timeline_data = viz_gen.get_timeline_data()
                    except Exception as e:
                        logger.warning("Could not get timeline data for interactive timeline: %s", e)
                        timeline_data = None
                    try:
                        mitre_stats = viz_gen.generate_mitre_statistics()
                    except Exception as e:
                        logger.warning("Could not generate MITRE statistics: %s", e)
            except Exception as e:
                logger.exception("Could not initialize visualization generator: %s", e)
        recommendations_content = report_data.get("recommendations_content")
        rec_path = Path(recommendations_file_path) if recommendations_file_path else None
        if recommendations_content is None and rec_path and rec_path.is_file():
            try:
                recommendations_content = rec_path.read_text(encoding="utf-8")
                logger.info("Loaded recommendations from: %s", recommendations_file_path)
            except Exception as e:
                logger.warning("Could not load recommendations file: %s", e)
                recommendations_content = None
        investigation_summary_file_path = report_data.get("investigation_summary_file_path")
        investigation_summary_content = None
        inv_path = Path(investigation_summary_file_path) if investigation_summary_file_path else None
        if inv_path and inv_path.is_file():
            try:
                investigation_summary_content = inv_path.read_text(encoding="utf-8")
                investigation_summary_content = defang_text(investigation_summary_content)
                logger.info("Loaded investigation summary from: %s", investigation_summary_file_path)
            except Exception as e:
                logger.warning("Could not load investigation summary file: %s", e)
                investigation_summary_content = None
        
        diamond_facets = self.parse_diamond_model_section(investigation_summary_content) if investigation_summary_content else None
        diamond_model_html = self.build_diamond_model_html(diamond_facets, report_color, investigation_summary_file_path) if diamond_facets else ""
        
        case_summary_section = f"""
            <div class="section">
                <div class="section-title">Case Summary</div>
                <div class="summary-box">
                    {summary_html}
                </div>
            </div>
""" if investigation_summary_file_path else ""
        
        timeline_data_json = (json.dumps(timeline_data).replace("</", "<\\/") if timeline_data else None)
        network_data_json = (json.dumps(network_data).replace("</", "<\\/") if network_data else None)
        vis_network_script = '<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>' if network_data else ''
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_esc}</title>
    {font_link}
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {font_family};
            line-height: 1.7;
            color: #1a1a1a;
            background: #f5f5f5;
            padding: 30px 20px;
            min-height: 100vh;
        }}
        
        .report-container {{
            max-width: 1680px;
            margin: 0 auto;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border: 1px solid #e0e0e0;
            overflow: hidden;
        }}
        .report-container.report-full-width {{
            max-width: none;
            width: 100%;
        }}
        
        .header {{
            background: #235AAA;
            color: #ffffff;
            padding: 50px 40px;
            text-align: center;
            border-bottom: 4px solid #235AAA;
        }}
        
        .header h1 {{
            font-size: 2.2em;
            font-weight: 600;
            margin-bottom: 15px;
            letter-spacing: 0.5px;
            color: #ffffff;
        }}
        
        .header-meta {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .header-meta-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9em;
            opacity: 0.9;
            color: #ecf0f1;
        }}
        
        .header-meta-item strong {{
            font-weight: 600;
            color: #ffffff;
        }}
        
        .content {{
            padding: 50px 40px;
        }}
        
        .section {{
            margin-bottom: 60px;
            page-break-inside: avoid;
        }}
        
        .section-title {{
            font-size: 1.6em;
            color: #235AAA;
            margin-bottom: 25px;
            padding-bottom: 12px;
            border-bottom: 2px solid #235AAA;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        .summary-box {{
            background: #f8f9fa;
            padding: 30px;
            margin-bottom: 35px;
            border-top: 1px solid #e0e0e0;
            border-right: 1px solid #e0e0e0;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .summary-box p {{
            font-size: 1.05em;
            line-height: 1.8;
            color: #333333;
            margin: 0 0 1em 0;
        }}
        .summary-box p:last-child {{
            margin-bottom: 0;
        }}
        .summary-box ul {{
            margin: 0.5em 0 1em 1.5em;
            padding-left: 1.5em;
        }}
        .summary-box li {{
            margin-bottom: 0.4em;
            line-height: 1.6;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin: 35px 0;
        }}
        
        .stat-card {{
            background: #ffffff;
            padding: 25px;
            text-align: center;
            border: 1px solid #e0e0e0;
            border-top: 3px solid #235AAA;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}
        
        .stat-value {{
            font-size: 2.4em;
            font-weight: 600;
            color: #235AAA;
            margin: 10px 0;
            line-height: 1;
        }}
        
        .stat-label {{
            font-size: 0.85em;
            color: #666;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-top: 8px;
        }}
        
        .visualization-container {{
            background: #ffffff;
            padding: 30px;
            margin: 35px 0;
            border: 1px solid #e0e0e0;
        }}
        
        .visualization-container h3 {{
            color: #235AAA;
            margin-bottom: 15px;
            font-size: 1.25em;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        .visualization-container p {{
            color: #666;
            margin-bottom: 20px;
            font-size: 0.95em;
        }}
        
        .visualization-image {{
            width: 100%;
            max-width: 100%;
            height: auto;
            border: 1px solid #d0d0d0;
            margin-top: 15px;
        }}
        
        /* Incident timeline (interactive) */
        .incident-timeline {{
            margin: 20px 0;
            position: relative;
        }}
        .incident-timeline::before {{
            content: '';
            position: absolute;
            left: calc(190px + 16px + 20px - 1px);
            top: 0;
            bottom: 0;
            width: 2px;
            background: #d0d0d0;
            z-index: 0;
        }}
        
        .incident-timeline-item {{
            display: grid;
            grid-template-columns: 190px 40px 1fr;
            column-gap: 16px;
            align-items: flex-start;
            margin-bottom: 24px;
        }}
        
        .incident-timeline-time {{
            text-align: right;
            font-size: 0.9em;
            font-weight: 600;
            color: #c62828;
            padding-right: 8px;
            white-space: nowrap;
        }}
        
        .incident-timeline-marker {{
            position: relative;
            min-height: 32px;
            z-index: 1;
        }}
        
        .incident-timeline-marker-line {{
            display: none;
        }}
        
        .incident-timeline-marker-dot {{
            position: relative;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #1976D2;
            border: 2px solid #1976D2;
            margin: 4px auto 0 auto;
            z-index: 1;
        }}
        
        .incident-timeline-content {{
            font-size: 0.95em;
            color: #333;
        }}
        
        .incident-timeline-tactic {{
            display: inline-block;
            background: #235AAA;
            color: #ffffff;
            padding: 4px 10px;
            border-radius: 3px;
            font-weight: 600;
            margin-bottom: 4px;
            font-size: 0.9em;
        }}
        
        .incident-timeline-activity {{
            margin-top: 4px;
        }}
        
        @media (max-width: 900px) {{
            .incident-timeline::before {{
                display: none;
            }}
            .incident-timeline-item {{
                grid-template-columns: 1fr;
            }}
            .incident-timeline-time {{
                text-align: left;
                margin-bottom: 4px;
            }}
            .incident-timeline-marker {{
                display: none;
            }}
        }}
        
        .network-vis-wrapper {{
            position: relative;
            margin-top: 15px;
        }}
        .network-vis-wrapper canvas {{
            cursor: default;
        }}
        .network-enlarge-btn {{
            display: inline-block;
            margin-bottom: 10px;
            padding: 8px 16px;
            background: #235AAA;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        }}
        .network-enlarge-btn:hover {{
            background: #235AAA;
        }}
        .network-enlarge-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 10000;
            justify-content: center;
            align-items: center;
        }}
        .network-enlarge-modal.is-open {{
            display: flex;
        }}
        .network-enlarge-modal .modal-content {{
            background: #fff;
            width: 90vw;
            height: 85vh;
            max-width: 1400px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .network-enlarge-modal .modal-header {{
            padding: 12px 20px;
            background: #235AAA;
            color: #fff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .network-enlarge-modal .modal-body {{
            flex: 1;
            min-height: 0;
        }}
        .network-enlarge-modal .modal-body .enlarge-network-container {{
            width: 100%;
            height: 100%;
            min-height: 400px;
        }}
        .network-enlarge-modal .modal-close {{
            background: #fff;
            color: #333;
            border: 1px solid #ccc;
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 4px;
        }}
        
        .data-table-container {{
            overflow-x: auto;
            margin: 35px 0;
            border: 1px solid #e0e0e0;
        }}
        
        .veris-table-container {{
            max-width: 60%;
            margin-left: auto;
            margin-right: auto;
        }}
        
        td.hash-cell {{
            white-space: normal;
        }}
        
        .hash-tag {{
            display: inline-block;
            background-color: {report_color_tag_bg};
            color: {report_color};
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.9em;
            margin-right: 8px;
            margin-bottom: 4px;
        }}
        
        .diamond-model-wrapper {{
            margin: 30px 0 50px 0;
        }}
        
        .diamond-model-section {{
            position: relative;
            min-height: 820px;
            max-width: 900px;
            margin: 0 auto;
        }}
        
        .diamond-model-center {{
            position: absolute;
            left: 50%;
            top: 56%;
            width: 448px;
            height: 448px;
            margin-left: -224px;
            margin-top: -224px;
            background: #f5f5f5;
            border: 2px solid #ccc;
            transform: rotate(45deg);
        }}
        
        .diamond-model-center--image {{
            background: transparent;
            border: none;
            transform: none;
        }}
        
        .diamond-model-center--image img {{
            width: 448px;
            height: 448px;
            display: block;
            object-fit: contain;
        }}
        
        .diamond-facet {{
            position: absolute;
            width: 220px;
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            padding: 12px;
        }}
        
        .diamond-facet-title {{
            background: #c62828;
            color: #fff;
            font-weight: 700;
            font-size: 0.95em;
            padding: 8px 12px;
            margin: -12px -12px 12px -12px;
            border-radius: 6px 6px 0 0;
        }}
        
        .diamond-facet-content {{
            font-size: 0.9em;
            color: #333;
            line-height: 1.5;
        }}
        
        .diamond-facet-content ul, .diamond-facet-content ol {{
            margin: 6px 0 0 16px;
            padding: 0;
        }}
        
        .diamond-facet-content p {{
            margin: 0 0 6px 0;
        }}
        
        .diamond-facet-top {{
            left: 50%;
            top: 0;
            margin-left: -110px;
            max-height: calc(56% - 224px - 20px);
            overflow-y: auto;
        }}
        
        .diamond-facet-left {{
            left: 0;
            top: 50%;
            margin-top: -80px;
        }}
        
        .diamond-facet-right {{
            right: 0;
            top: 50%;
            margin-top: -80px;
        }}
        
        .diamond-facet-bottom {{
            left: 50%;
            top: calc(56% + 224px + 16px);
            bottom: auto;
            margin-left: -110px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            font-size: 0.9em;
        }}
        
        thead {{
            background: #235AAA;
            color: white;
        }}
        
        th {{
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 0.8px;
            position: sticky;
            top: 0;
            z-index: 10;
            border-bottom: 2px solid #235AAA;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e8e8e8;
            color: #333;
        }}
        
        tbody tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        tbody tr:hover {{
            background-color: #f0f0f0;
        }}
        
        .sheet-header {{
            background: #f8f9fa;
            padding: 20px 25px;
            border-bottom: 2px solid #235AAA;
            border-top: 1px solid #e0e0e0;
            border-left: 1px solid #e0e0e0;
            border-right: 1px solid #e0e0e0;
        }}
        
        .sheet-header h2 {{
            color: #235AAA;
            font-size: 1.4em;
            margin-bottom: 8px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        .sheet-header .row-count {{
            color: #666;
            font-size: 0.9em;
        }}
        
        .tactics-table {{
            margin-top: 20px;
        }}
        
        .tactics-table thead {{
            background: #235AAA;
        }}
        
        .mitre-section {{
            padding: 0 0 0 0;
            margin-top: 0;
            margin-bottom: 60px;
        }}
        
        .mitre-section .section-title {{
            margin-bottom: 25px;
            letter-spacing: 0.3px;
        }}
        
        .mitre-header {{
            text-align: center;
            margin: 28px 0 24px;
        }}
        
        .mitre-stats {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .mitre-stat-pill {{
            background: #ffffff;
            border-radius: 10px;
            padding: 18px 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border: 1px solid #e8ecf0;
            min-width: 140px;
            text-align: center;
        }}
        
        .mitre-stat-pill-value {{
            display: block;
            font-size: 2em;
            font-weight: 700;
            color: #235AAA;
            line-height: 1.2;
        }}
        
        .mitre-stat-pill-label {{
            font-size: 0.85em;
            color: #607d8b;
            font-weight: 500;
            margin-top: 4px;
            letter-spacing: 0.3px;
        }}
        
        .mitre-intro {{
            font-size: 0.98em;
            color: #546e7a;
            margin-top: 8px;
            max-width: 520px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.5;
        }}
        
        .tactics-container {{
            margin: 32px 0 0;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}
        
        @media (max-width: 900px) {{
            .tactics-container {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .tactic-card {{
            background: #ffffff;
            border-radius: 8px;
            padding: 20px 22px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border-left: 4px solid #235AAA;
            break-inside: avoid;
        }}
        
        .tactic-card:nth-child(3n+2) {{
            border-left-color: #00695c;
        }}
        
        .tactic-card:nth-child(3n+3) {{
            border-left-color: #37474f;
        }}
        
        .tactic-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }}
        
        .tactic-card-title {{
            font-size: 1.1em;
            color: #235AAA;
            font-weight: 600;
            letter-spacing: 0.2px;
            margin: 0;
        }}
        
        .tactic-count-badge {{
            background: #e3f2fd;
            color: #235AAA;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
        }}
        
        .tactic-card:nth-child(3n+2) .tactic-count-badge {{
            background: #e0f2f1;
            color: #00695c;
        }}
        
        .tactic-card:nth-child(3n+3) .tactic-count-badge {{
            background: #eceff1;
            color: #37474f;
        }}
        
        .techniques-list {{
            margin: 0;
            padding: 0;
            list-style: none;
        }}
        
        .techniques-list li {{
            position: relative;
            padding-left: 18px;
            margin: 8px 0;
            color: #455a64;
            font-size: 0.95em;
            line-height: 1.6;
        }}
        
        .techniques-list li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0.55em;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #90a4ae;
        }}
        
        .mitre-attribution {{
            text-align: right;
            margin-top: 28px;
            padding-top: 16px;
            border-top: 1px solid #e8ecf0;
            color: #78909c;
            font-size: 0.8em;
        }}
        
        .mitre-attribution a {{
            color: #607d8b;
            text-decoration: none;
        }}
        
        .mitre-attribution a:hover {{
            color: #235AAA;
            text-decoration: underline;
        }}
        
        .markdown-content {{
            background: #ffffff;
            padding: 30px;
            border: 1px solid #e0e0e0;
            line-height: 1.8;
        }}
        
        .markdown-content h1,
        .markdown-content h2,
        .markdown-content h3,
        .markdown-content h4,
        .markdown-content h5,
        .markdown-content h6 {{
            color: #235AAA;
            margin-top: 25px;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .markdown-content h1 {{
            font-size: 1.8em;
            border-bottom: 2px solid #235AAA;
            padding-bottom: 10px;
        }}
        .markdown-content h1:first-child,
        .markdown-content h2:first-child {{
            border-bottom: none;
            padding-bottom: 0;
            margin-top: 0;
        }}
        
        .markdown-content h2 {{
            font-size: 1.5em;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        
        .markdown-content h3 {{
            font-size: 1.3em;
            margin-top: 25px;
        }}
        
        .markdown-content h4 {{
            font-size: 1.1em;
        }}
        
        .markdown-content p {{
            margin-bottom: 15px;
            color: #333;
        }}
        
        .markdown-content ul,
        .markdown-content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        .markdown-content li {{
            margin: 8px 0;
            color: #444;
        }}
        
        .markdown-content code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #c7254e;
        }}
        
        .markdown-content pre {{
            background: #f8f9fa;
            padding: 15px;
            border: 1px solid #e0e0e0;
            border-left: 4px solid #235AAA;
            overflow-x: auto;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .markdown-content pre code {{
            background: transparent;
            padding: 0;
            color: #333;
            font-size: 0.9em;
        }}
        
        .markdown-content blockquote {{
            border-left: 4px solid #235AAA;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
            background: #f8f9fa;
            padding: 15px 20px;
        }}
        
        .markdown-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        .markdown-content table th,
        .markdown-content table td {{
            border: 1px solid #e0e0e0;
            padding: 10px;
            text-align: left;
        }}
        
        .markdown-content table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #235AAA;
        }}
        
        .markdown-content table tr:nth-child(even) {{
            background: #fafafa;
        }}
        
        .markdown-content hr {{
            display: none;
        }}
        
        .markdown-content img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #e0e0e0;
            margin: 20px auto;
            display: block;
            border-radius: 4px;
        }}
        
        .markdown-content a {{
            color: #235AAA;
            text-decoration: none;
            border-bottom: 1px solid #235AAA;
        }}
        
        .markdown-content a:hover {{
            color: #235AAA;
            border-bottom: 2px solid #235AAA;
        }}
        
        .markdown-content strong {{
            font-weight: 600;
            color: #235AAA;
        }}
        
        .markdown-content em {{
            font-style: italic;
            color: #555;
        }}
        
        .markdown-content .recommendation-meta {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            padding: 8px 14px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #6c757d;
        }}
        .markdown-content .recommendation-meta-label {{
            font-weight: 600;
            color: #495057;
        }}
        .markdown-content .recommendation-meta-value {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
            background: #6c757d;
            color: #fff;
        }}
        .markdown-content .recommendation-meta-value.recommendation-criticality-critical {{
            background: #b71c1c;
            color: #fff;
        }}
        .markdown-content .recommendation-meta-value.recommendation-criticality-high {{
            background: #e65100;
            color: #fff;
        }}
        .markdown-content .recommendation-meta-value.recommendation-criticality-medium {{
            background: #f9a825;
            color: #1a1a1a;
        }}
        .markdown-content .recommendation-meta-value.recommendation-criticality-low {{
            background: #2e7d32;
            color: #fff;
        }}
        
        .collapsible-recommendations-header {{
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .collapsible-recommendations-header:hover {{
            opacity: 0.9;
        }}
        .collapsible-toggle {{
            font-size: 0.85em;
            transition: transform 0.2s;
        }}
        .collapsible-recommendations-content.collapsed {{
            display: none;
        }}
        
        .images-full-size .visualization-container {{
            overflow-x: auto;
        }}
        .images-full-size .visualization-image {{
            max-width: none;
            width: auto;
            height: auto;
        }}
        .images-full-size .markdown-content {{
            overflow-x: auto;
        }}
        .images-full-size .markdown-content img {{
            max-width: none;
            width: auto;
            height: auto;
            margin-left: auto;
            margin-right: auto;
        }}
        
        .footer {{
            background: #235AAA;
            color: #ecf0f1;
            padding: 30px;
            text-align: center;
            margin-top: 60px;
            border-top: 4px solid #235AAA;
        }}
        
        .footer p {{
            margin: 5px 0;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .report-container {{
                box-shadow: none;
                border: none;
            }}
            .header {{
                background: #235AAA !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            thead {{
                background: #235AAA !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .section {{
                page-break-inside: avoid;
            }}
            table {{
                page-break-inside: auto;
            }}
            tr {{
                page-break-inside: avoid;
                page-break-after: auto;
            }}
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 15px 10px;
            }}
            .header {{
                padding: 30px 20px;
            }}
            .header h1 {{
                font-size: 1.8em;
            }}
            .header-meta {{
                flex-direction: column;
                gap: 10px;
            }}
            .content {{
                padding: 30px 20px;
            }}
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            .section-title {{
                font-size: 1.4em;
            }}
            .diamond-model-section {{
                min-height: auto;
            }}
            .diamond-facet {{
                position: relative;
                width: 100%;
                max-width: 280px;
                margin: 12px auto;
                left: auto !important;
                right: auto !important;
                top: auto !important;
                bottom: auto !important;
                margin-left: auto !important;
                margin-top: 12px !important;
                margin-bottom: 12px !important;
            }}
        }}
    </style>
{vis_network_script}
</head>
<body>
    <div class="{container_class}">{header_html}
        <div class="content">
            {case_summary_section}
"""
        if show_timeline_section and timeline_data_json:
            html += f"""
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Incident Timeline
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="visualization-container">
                    <div id="incident-timeline-container" class="incident-timeline"></div>
                    <script>
(function() {{
    var container = document.getElementById('incident-timeline-container');
    if (!container) return;
    var timelineData = {timeline_data_json};
    if (!Array.isArray(timelineData) || !timelineData.length) return;
    timelineData.forEach(function(ev) {{
        var item = document.createElement('div');
        item.className = 'incident-timeline-item';

        var time = document.createElement('div');
        time.className = 'incident-timeline-time';
        time.textContent = ev.timestamp_display || ev.timestamp || '';
        item.appendChild(time);

        var marker = document.createElement('div');
        marker.className = 'incident-timeline-marker';
        var line = document.createElement('div');
        line.className = 'incident-timeline-marker-line';
        var dot = document.createElement('div');
        dot.className = 'incident-timeline-marker-dot';
        marker.appendChild(line);
        marker.appendChild(dot);
        item.appendChild(marker);

        var content = document.createElement('div');
        content.className = 'incident-timeline-content';
        var tactic = document.createElement('div');
        tactic.className = 'incident-timeline-tactic';
        tactic.textContent = ev.mitre_tactic || '';
        var desc = document.createElement('div');
        desc.className = 'incident-timeline-activity';
        desc.textContent = ev.activity || '';
        content.appendChild(tactic);
        content.appendChild(desc);
        item.appendChild(content);

        container.appendChild(item);
    }});
}})();
                    </script>
                </div>
                </div>
            </div>
"""
        elif show_timeline_section and timeline_img:
            html += f"""
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Incident Timeline
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="visualization-container">
                    <img src="{timeline_img}" alt="Incident Timeline" class="visualization-image" />
                </div>
                </div>
            </div>
"""
        if show_lateral_section and network_data:
            html += f"""
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▼</span>
                    Lateral Movement
                </div>
                <div class="collapsible-recommendations-content">
                <div class="visualization-container">
                    <button type="button" class="network-enlarge-btn" id="network-enlarge-btn" aria-label="Enlarge network">Enlarge</button>
                    <div class="network-vis-wrapper">
                        <div id="network-vis-container" style="width:100%;height:600px;min-height:480px;"></div>
                    </div>
                    <div class="network-enlarge-modal" id="network-enlarge-modal" aria-hidden="true">
                        <div class="modal-content">
                            <div class="modal-header">
                                <span>Network Topology (enlarged)</span>
                                <button type="button" class="modal-close" id="network-enlarge-close">Close</button>
                            </div>
                            <div class="modal-body">
                                <div id="network-vis-enlarge-container" class="enlarge-network-container"></div>
                            </div>
                        </div>
                    </div>
                    <script>
(function() {{
    var networkData = {network_data_json};
    window._networkDataEnlarge = networkData;
    var container = document.getElementById('network-vis-container');
    var physicsOptions = {{ enabled: true, barnesHut: {{ springLength: 180, gravitationalConstant: -5000 }} }};
    var options = {{ physics: physicsOptions, nodes: {{ font: {{ size: 14 }} }} }};
    if (container && typeof vis !== 'undefined') {{
        var nodes = new vis.DataSet(networkData.nodes);
        var edges = new vis.DataSet(networkData.edges);
        var data = {{ nodes: nodes, edges: edges }};
        var network = new vis.Network(container, data, options);
    }}
    var enlargeBtn = document.getElementById('network-enlarge-btn');
    var modal = document.getElementById('network-enlarge-modal');
    var closeBtn = document.getElementById('network-enlarge-close');
    var enlargeContainer = document.getElementById('network-vis-enlarge-container');
    var enlargeNetwork = null;
    function openEnlarge() {{
        if (typeof vis === 'undefined' || !window._networkDataEnlarge) return;
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        enlargeContainer.innerHTML = '';
        var nodes = new vis.DataSet(window._networkDataEnlarge.nodes);
        var edges = new vis.DataSet(window._networkDataEnlarge.edges);
        var data = {{ nodes: nodes, edges: edges }};
        enlargeNetwork = new vis.Network(enlargeContainer, data, options);
    }}
    function closeEnlarge() {{
        if (enlargeNetwork) {{ enlargeNetwork.destroy(); enlargeNetwork = null; }}
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
    }}
    if (enlargeBtn) enlargeBtn.addEventListener('click', openEnlarge);
    if (closeBtn) closeBtn.addEventListener('click', closeEnlarge);
    if (modal) modal.addEventListener('click', function(e) {{ if (e.target === modal) closeEnlarge(); }});
}})();
                    </script>
                </div>
                </div>
            </div>
"""
        elif show_lateral_section and network_img:
            html += f"""
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▼</span>
                    Lateral Movement
                </div>
                <div class="collapsible-recommendations-content">
                <div class="visualization-container">
                    <h3>Network Topology</h3>
                    <p>Network connections and relationships between systems in the incident.</p>
                    <img src="{network_img}" alt="Lateral Movement" class="visualization-image" />
                </div>
                </div>
            </div>
"""
        
        if investigation_summary_content:
            investigation_content_without_diamond = self.strip_markdown_section(
                investigation_summary_content, "Diamond Model", include_subsections=True
            )
            investigation_content_filtered = self.strip_markdown_section(
                investigation_content_without_diamond, "Case Summary", include_subsections=False
            )
            html += """
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Investigation Summary
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="markdown-content">
"""
            html += self.convert_markdown_to_html(
                investigation_content_filtered, investigation_summary_file_path
            )
            
            html += """
                </div>
                </div>
            </div>
"""
        if recommendations_content:
            recommendations_content = self.sort_recommendations_by_criticality(recommendations_content)
            html += """
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Recommendations
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="markdown-content">
"""
            html += self.convert_markdown_to_html(recommendations_content, recommendations_file_path)
            html += """
                </div>
                </div>
            </div>
"""
        SYSTEMS_DISPLAY_COLUMNS = [
            config.COL_HOSTNAME,
            config.COL_IP_ADDRESS,
            "OS",
            config.COL_ENTRY_POINT,
            config.COL_EVIDENCE_COLLECTED,
            config.COL_NOTES,
        ]
        ACCOUNTS_DISPLAY_COLUMNS = [
            "AccountName",
            "UserName",
            "SID",
            config.COL_ACCOUNT_TYPE,
        ]
        EVIDENCE_TRACKER_DISPLAY_COLUMNS = [
            "Evidence ID",
            "EvidenceName",
            "EvidenceFormat",
            config.COL_DATE_REQUESTED,
            config.COL_DATE_RECEIVED,
            "Evidence Hash (If applicible)",
        ]
        INDICATORS_HASH_COLUMNS = ["SHA256", "SHA1", "MD5"]
        INDICATORS_DISPLAY_ORDER = ["IndicatorType", "Indicator", "Hash"]
        mitre_section_added = False
        diamond_section_added = False
        for sheet_name, sheet_data in report_data.get("sheets", {}).items():
            if sheet_name == config.SHEET_TIMELINE:
                continue
            if sheet_name == config.SHEET_EVIDENCE_TRACKER:
                if diamond_model_html:
                    html += f"""
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Diamond Model
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="diamond-model-wrapper">
                    {diamond_model_html}
                </div>
                </div>
            </div>
"""
                    diamond_section_added = True
                if show_mitre_section and mitre_stats and mitre_stats.get('total_detections', 0) > 0 and not mitre_section_added:
                    total_detections = mitre_stats.get('total_detections', 0)
                    tactics_techniques = mitre_stats.get('tactics_techniques', {})
                    unique_tactics = len(tactics_techniques) if tactics_techniques else 0
                    html += f"""
            <div class="section mitre-section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    MITRE ATT&CK Tactics & Techniques Mapping
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="mitre-header">
                    <div class="mitre-stats">
                        <div class="mitre-stat-pill">
                            <span class="mitre-stat-pill-value">{total_detections}</span>
                            <span class="mitre-stat-pill-label">Detections</span>
                        </div>
                        <div class="mitre-stat-pill">
                            <span class="mitre-stat-pill-value">{unique_tactics}</span>
                            <span class="mitre-stat-pill-label">Tactics</span>
                        </div>
                    </div>
                    <p class="mitre-intro">The following MITRE ATT&CK tactics and techniques were identified in this incident.</p>
                </div>
                
                <div class="tactics-container">
"""
                    if tactics_techniques:
                        for tactic, techniques in tactics_techniques.items():
                            tech_count = len(techniques) if techniques else 0
                            html += f"""
                    <div class="tactic-card">
                        <div class="tactic-card-header">
                            <span class="tactic-card-title">{html_module.escape(str(tactic))}</span>
                            <span class="tactic-count-badge">{tech_count} technique{"s" if tech_count != 1 else ""}</span>
                        </div>
"""
                            if techniques:
                                html += """
                        <ul class="techniques-list">
"""
                                for technique in techniques:
                                    html += f"""
                            <li>{html_module.escape(str(technique))}</li>
"""
                                html += """
                        </ul>
"""
                            html += """
                    </div>
"""
                    html += """
                </div>
                
                <div class="mitre-attribution">
                    <p>Based on MITRE ATT&CK® Framework - <a href="https://attack.mitre.org/" target="_blank">attack.mitre.org</a></p>
                </div>
                </div>
            </div>
"""
                    mitre_section_added = True
            df = pd.DataFrame(sheet_data['data'], columns=sheet_data['columns'])
            if sheet_name == config.SHEET_SYSTEMS:
                # Exclude rows for Compromised Systems report section (before restricting columns)
                if config.COL_SYSTEM_TYPE in df.columns:
                    df = df[df[config.COL_SYSTEM_TYPE].astype(str).str.strip() != "Attacker-Machine"]
                if config.COL_LOCATION in df.columns:
                    df = df[df[config.COL_LOCATION].astype(str).str.strip() != "3rd Party Applications - Cloud"]
                available = [c for c in SYSTEMS_DISPLAY_COLUMNS if c in df.columns]
                if available:
                    df = df[available]
            elif sheet_name == config.SHEET_ACCOUNTS:
                available = [c for c in ACCOUNTS_DISPLAY_COLUMNS if c in df.columns]
                if available:
                    df = df[available]
            elif sheet_name == config.SHEET_EVIDENCE_TRACKER:
                available = [c for c in EVIDENCE_TRACKER_DISPLAY_COLUMNS if c in df.columns]
                if available:
                    df = df[available]
                if "Evidence ID" in df.columns:
                    df = df.sort_values(by="Evidence ID").reset_index(drop=True)
            elif sheet_name == config.SHEET_INDICATORS:
                hash_cols = [c for c in INDICATORS_HASH_COLUMNS if c in df.columns]
                if hash_cols:
                    def merge_hashes(row):
                        parts = []
                        for col in hash_cols:
                            val = row.get(col)
                            if pd.notna(val) and str(val).strip():
                                parts.append(f"{col}: {str(val).strip()}")
                        return "\n".join(parts) if parts else ""
                    df = df.copy()
                    df["Hash"] = df.apply(merge_hashes, axis=1)
                available = [c for c in INDICATORS_DISPLAY_ORDER if c in df.columns]
                if available:
                    pass
                if "IndicatorType" in df.columns:
                    def indicator_type_sort_key(series):
                        def key_val(v):
                            s = str(v).strip().lower() if pd.notna(v) else ""
                            if s in ("other-strings", "other strings"):
                                return (1, s)
                            return (0, s)
                        return series.map(key_val)
                    df = df.sort_values(by="IndicatorType", key=indicator_type_sort_key).reset_index(drop=True)
            if sheet_name == "VERIS" and "meta-value" in df.columns:
                df = df[df["meta-value"].astype(str).str.strip().str.lower() != "unknown"]
            display_name = self.get_sheet_display_name(sheet_name)
            table_columns = [c for c in INDICATORS_DISPLAY_ORDER if c in df.columns] if sheet_name == config.SHEET_INDICATORS else list(df.columns)
            is_veris = sheet_name == "VERIS"
            is_evidence_tracker = sheet_name == config.SHEET_EVIDENCE_TRACKER
            is_collapsible = (
                is_veris or is_evidence_tracker
                or sheet_name == config.SHEET_INDICATORS
                or sheet_name == config.SHEET_ACCOUNTS
                or sheet_name == config.SHEET_SYSTEMS
            )
            section_extra_class = " collapsible-recommendations" if is_collapsible else ""
            header_extra_class = " collapsible-recommendations-header" if is_collapsible else ""
            toggle_span = '<span class="collapsible-toggle" aria-hidden="true">▶</span>\n                    ' if is_collapsible else ""
            content_wrapper_open = '\n                <div class="collapsible-recommendations-content collapsed">' if is_collapsible else ""
            html += f"""
            <div class="section{section_extra_class}">
                <div class="section-title{header_extra_class}">
                    {toggle_span}{display_name}
                </div>{content_wrapper_open}
                <div class="data-table-container{f' veris-table-container' if is_veris else ''}">
                    <table>
                        <thead>
                            <tr>
"""
            for col in table_columns:
                th_class = ' class="hash-cell"' if col == "Hash" else ""
                col_header = col
                if is_veris:
                    if col and str(col).strip().lower() == "meta":
                        col_header = "Attributes"
                    elif col and str(col).strip().lower() == "meta-value":
                        col_header = "Values"
                html += f"                                <th{th_class}>{col_header}</th>\n"
            
            html += """                            </tr>
                        </thead>
                        <tbody>
"""
            max_rows = min(1000, len(df))
            for idx, row in df.head(max_rows).iterrows():
                html += "                            <tr>\n"
                for col in table_columns:
                    value = str(row[col]) if pd.notna(row[col]) else ""
                    if sheet_name == config.SHEET_EVIDENCE_TRACKER and col == config.COL_DATE_RECEIVED and (not value or not value.strip()):
                        value = '<span class="hash-tag">Pending</span>'
                        td_class = ""
                    else:
                        if sheet_name == config.SHEET_INDICATORS and col == "Indicator" and value:
                            indicator_type = str(row.get("IndicatorType", "")).strip() if pd.notna(row.get("IndicatorType")) else ""
                            if indicator_type.lower().replace(" ", "") in IOC_DEFANG_TYPES:
                                value = defang_text(value)
                        value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        if col == "Hash" and value:
                            lines = [ln.strip() for ln in value.split("\n") if ln.strip()]
                            if lines:
                                parts = []
                                for ln in lines:
                                    if ": " in ln:
                                        label, val = ln.split(": ", 1)
                                        parts.append(f'{val.strip()} <span class="hash-tag">{label.strip()}</span>')
                                    else:
                                        parts.append(f'<span class="hash-tag">{ln}</span>')
                                value = "<br>".join(parts)
                            td_class = ' class="hash-cell"'
                        elif sheet_name == config.SHEET_INDICATORS and col == "Indicator":
                            notes_val = str(row.get("Notes", "")) if pd.notna(row.get("Notes")) else ""
                            if notes_val.strip():
                                notes_esc = notes_val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                if len(notes_esc) > 200:
                                    notes_esc = notes_esc[:197] + "..."
                                value = f"{value} <span class=\"hash-tag\">{notes_esc}</span>"
                                td_class = ""
                        else:
                            if len(value) > 200:
                                value = value[:197] + "..."
                            td_class = ' class="hash-cell"' if col == "Hash" else ""
                    html += f"                                <td{td_class}>{value}</td>\n"
                html += "                            </tr>\n"
            
            if len(df) > max_rows:
                html += f"""
                            <tr>
                                <td colspan="{len(table_columns)}" style="text-align: center; font-style: italic; color: #666; padding: 20px; background: #f8f9fa;">
                                    <strong>Note:</strong> Showing first {max_rows} of {len(df)} rows. Full data available in source Excel file.
                                </td>
                            </tr>
"""
            
            content_wrapper_close = "\n                </div>" if is_collapsible else ""
            html += f"""                        </tbody>
                    </table>
                </div>{content_wrapper_close}
            </div>
"""
        if diamond_model_html and not diamond_section_added:
            html += f"""
            <div class="section collapsible-recommendations">
                <div class="section-title collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Diamond Model
                </div>
                <div class="collapsible-recommendations-content collapsed">
                <div class="diamond-model-wrapper">
                    {diamond_model_html}
                </div>
                </div>
            </div>
"""

        html += f"""
        </div>
        {footer_html}
    </div>
    <script>
    document.querySelectorAll('.collapsible-recommendations-header').forEach(function(h, idx) {{
        var content = h.nextElementSibling;
        var toggle = h.querySelector('.collapsible-toggle');
        if (!content || !toggle) return;
        if (!content.id) content.id = 'collapsible-content-' + idx;
        h.setAttribute('role', 'button');
        h.setAttribute('tabindex', '0');
        h.setAttribute('aria-expanded', content.classList.contains('collapsed') ? 'false' : 'true');
        h.setAttribute('aria-controls', content.id);
        function toggleContent() {{
            content.classList.toggle('collapsed');
            toggle.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
            h.setAttribute('aria-expanded', content.classList.contains('collapsed') ? 'false' : 'true');
        }}
        h.addEventListener('click', toggleContent);
        h.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' || e.key === ' ') {{
                e.preventDefault();
                toggleContent();
            }}
        }});
    }});
    </script>
</body>
</html>
"""
        
        html = html.replace("#235AAA", report_color)
        html = html.replace("#c62828", report_color)
        return html
    
    def build_debrief_html(self, report_data: Dict[str, Any], workbook=None) -> str:
        title = report_data.get("title", "KANVAS Daily Debrief")
        author = report_data.get("author", "KANVAS User")
        title_esc = html_module.escape(title)
        author_esc = html_module.escape(author)
        summary_raw = report_data.get("summary", "No summary provided.")
        investigation_summary_file_path = report_data.get("investigation_summary_file_path")
        if summary_raw and summary_raw.strip() and summary_raw.strip() != "No summary provided.":
            summary_for_html = defang_text(summary_raw.strip())
            summary_html = self.convert_markdown_to_html(
                summary_for_html, investigation_summary_file_path
            )
        else:
            summary_html = self.summary_text_to_html(summary_raw or "No summary provided.")
        excel_file_name = report_data.get("excel_file_name", "N/A")
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_only = datetime.now().strftime('%Y-%m-%d')
        timeline_img = None
        network_img = None
        network_data = None
        mitre_stats = {}
        timeline_image_path = report_data.get("timeline_image_path")
        network_image_path = report_data.get("network_image_path")
        recommendations_file_path = report_data.get("recommendations_file_path")
        timeline_path_debrief = Path(timeline_image_path) if timeline_image_path else None
        if timeline_path_debrief and timeline_path_debrief.is_file():
            try:
                img_data = base64.b64encode(timeline_path_debrief.read_bytes()).decode("utf-8")
                ext = timeline_path_debrief.suffix.lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                timeline_img = "data:%s;base64,%s" % (mime_type, img_data)
            except Exception as e:
                logger.warning("Could not load timeline image: %s", e)
        network_path_debrief = Path(network_image_path) if network_image_path else None
        if network_path_debrief and network_path_debrief.is_file():
            try:
                img_data = base64.b64encode(network_path_debrief.read_bytes()).decode("utf-8")
                ext = network_path_debrief.suffix.lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                network_img = "data:%s;base64,%s" % (mime_type, img_data)
            except Exception as e:
                logger.warning("Could not load network image: %s", e)
        if enable_visualizations and workbook and (show_timeline_section or show_lateral_section or show_mitre_section):
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=UserWarning)
                    db_path = report_data.get("db_path", "") or ""
                    viz_gen = VisualizationGenerator(workbook, db_path=db_path)
                    
                    if not timeline_img:
                        try:
                            timeline_img = viz_gen.generate_timeline_image()
                        except Exception:
                            pass
                    
                    if not network_img:
                        try:
                            network_img = viz_gen.generate_network_image()
                        except Exception:
                            pass
                    
                    try:
                        network_data = viz_gen.get_network_data()
                    except Exception:
                        network_data = None
                    
                    try:
                        mitre_stats = viz_gen.generate_mitre_statistics()
                    except Exception:
                        pass
            except Exception:
                pass
        
        network_data_json = (json.dumps(network_data).replace("</", "<\\/") if network_data else None)
        vis_network_script = '<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>' if network_data else ''
        recommendations_content = report_data.get("recommendations_content")
        rec_path_debrief = Path(recommendations_file_path) if recommendations_file_path else None
        if recommendations_content is None and rec_path_debrief and rec_path_debrief.is_file():
            try:
                recommendations_content = rec_path_debrief.read_text(encoding="utf-8")
                logger.info("Loaded recommendations from: %s", recommendations_file_path)
            except Exception as e:
                logger.warning("Could not load recommendations file: %s", e)
                recommendations_content = None
        investigation_summary_content = None
        inv_path_debrief = Path(investigation_summary_file_path) if investigation_summary_file_path else None
        if inv_path_debrief and inv_path_debrief.is_file():
            try:
                investigation_summary_content = inv_path_debrief.read_text(encoding="utf-8")
                investigation_summary_content = defang_text(investigation_summary_content)
                logger.info("Loaded investigation summary from: %s", investigation_summary_file_path)
            except Exception as e:
                logger.warning("Could not load investigation summary file: %s", e)
                investigation_summary_content = None
        total_rows = sum(len(sheet_data.get('data', [])) for sheet_data in report_data.get("sheets", {}).values())
        images_constrained = report_data.get("images_constrained", True)
        report_full_width = report_data.get("report_full_width", False)
        container_class_debrief = "debrief-container"
        if not images_constrained:
            container_class_debrief += " images-full-size"
        if report_full_width:
            container_class_debrief += " report-full-width"
        
        header_options = report_data.get("header_options") or {}
        footer_options = report_data.get("footer_options") or {}
        report_font = report_data.get("report_font", "Inter")
        report_color = report_data.get("report_color", "#235AAA")
        if report_font == "Inter":
            font_link_debrief = '<link rel="preconnect" href="https://fonts.googleapis.com">\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
            font_family_debrief = "'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
        else:
            font_link_debrief = ""
            font_stacks_debrief = {
                "Arial": "'Arial', Helvetica, sans-serif",
                "Georgia": "'Georgia', 'Times New Roman', serif",
                "Segoe UI": "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
                "Times New Roman": "'Times New Roman', Times, serif",
                "Verdana": "Verdana, Geneva, sans-serif",
            }
            font_family_debrief = font_stacks_debrief.get(report_font, "'%s', sans-serif" % report_font)
        if header_options.get("include_headers", True):
            debrief_meta_parts = []
            if header_options.get("author", True):
                debrief_meta_parts.append(f'<span><strong>Author:</strong> {author_esc}</span>')
            if header_options.get("generated", True):
                debrief_meta_parts.append(f'<span><strong>Time:</strong> {timestamp.split()[1] if " " in timestamp else ""}</span>')
            if header_options.get("source", True):
                src = Path(excel_file_name).name if excel_file_name and excel_file_name != "N/A" else "N/A"
                debrief_meta_parts.append('<span><strong>Source:</strong> %s</span>' % src)
            conf = (header_options.get("confidentiality") or "").strip()
            if conf:
                debrief_meta_parts.append(f'<span><strong>Confidentiality:</strong> {conf}</span>')
            if header_options.get("reviewed_by", True):
                rev_text = (header_options.get("reviewed_by_text") or "").strip()
                if rev_text:
                    debrief_meta_parts.append(f'<span><strong>Reviewed by:</strong> {html_module.escape(rev_text)}</span>')
            if header_options.get("case_id", True):
                case_text = (header_options.get("case_id_text") or "").strip()
                if case_text:
                    debrief_meta_parts.append(f'<span><strong>Case ID:</strong> {html_module.escape(case_text)}</span>')
            debrief_meta_html = "\n                ".join(debrief_meta_parts) if debrief_meta_parts else ""
            debrief_header_html = f"""
        <div class="debrief-header">
            <h1>{title_esc}</h1>
            <div class="date-badge">{date_only}</div>
            <div class="meta-info">
                {debrief_meta_html}
            </div>
        </div>
        
        """
        else:
            debrief_header_html = ""
        
        if footer_options.get("include_footers", True):
            debrief_footer_parts = []
            if footer_options.get("report_generated_on", True):
                debrief_footer_parts.append(f"<p>{timestamp}</p>")
            if footer_options.get("contact", True):
                contact_text = (footer_options.get("contact_text") or "").strip() or author
                debrief_footer_parts.append(f"<p>For questions or issues, please contact: {html_module.escape(contact_text)}</p>")
            if footer_options.get("contact_number", True):
                contact_num_text = (footer_options.get("contact_number_text") or "").strip()
                if contact_num_text:
                    debrief_footer_parts.append(f"<p><strong>Contact Number:</strong> {html_module.escape(contact_num_text)}</p>")
            if footer_options.get("website", True):
                website_text = (footer_options.get("website_text") or "").strip()
                if website_text:
                    debrief_footer_parts.append(f"<p><strong>Website:</strong> <a href=\"{html_module.escape(website_text)}\">{html_module.escape(website_text)}</a></p>")
            if footer_options.get("reviewed_by", True):
                rev_text = (footer_options.get("reviewed_by_text") or "").strip()
                if rev_text:
                    debrief_footer_parts.append(f"<p><strong>Reviewed by:</strong> {html_module.escape(rev_text)}</p>")
            if footer_options.get("case_id", True):
                case_text = (footer_options.get("case_id_text") or "").strip()
                if case_text:
                    debrief_footer_parts.append(f"<p><strong>Case ID:</strong> {html_module.escape(case_text)}</p>")
            debrief_footer_inner = "\n            ".join(debrief_footer_parts) if debrief_footer_parts else ""
            debrief_footer_html = f"""
        <div class="debrief-footer">
            {debrief_footer_inner}
        </div>
"""
        else:
            debrief_footer_html = ""
        debrief_case_summary_section = f"""
            <!-- Case Summary -->
            <div class="summary-section">
                <h2>📋 Case Summary</h2>
                {summary_html}
            </div>
""" if investigation_summary_file_path else ""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_esc} - {date_only}</title>
    {font_link_debrief}
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {font_family_debrief};
            line-height: 1.6;
            color: {report_color};
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 15px;
            min-height: 100vh;
        }}
        
        .debrief-container {{
            max-width: 1680px;
            margin: 0 auto;
            background: #ffffff;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            overflow: hidden;
        }}
        .debrief-container.report-full-width {{
            max-width: none;
            width: 100%;
        }}
        
        .debrief-header {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px 40px;
            text-align: center;
        }}
        
        .debrief-header h1 {{
            font-size: 2.2em;
            font-weight: 700;
            margin-bottom: 8px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .debrief-header .date-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 1.1em;
            font-weight: 600;
            margin-top: 10px;
            backdrop-filter: blur(10px);
        }}
        
        .debrief-header .meta-info {{
            display: flex;
            justify-content: center;
            gap: 25px;
            margin-top: 15px;
            flex-wrap: wrap;
            font-size: 0.9em;
            opacity: 0.95;
        }}
        
        .debrief-content {{
            padding: 35px 40px;
        }}
        
        .quick-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 35px;
        }}
        
        .quick-stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease;
        }}
        
        .quick-stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .quick-stat-value {{
            font-size: 2.8em;
            font-weight: 700;
            margin: 10px 0;
            line-height: 1;
        }}
        
        .quick-stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 8px;
        }}
        
        .summary-section {{
            background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 30px;
            border-left: 5px solid #e17055;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        
        .summary-section h2 {{
            color: #2d3436;
            font-size: 1.4em;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .summary-section p {{
            color: #2d3436;
            font-size: 1.05em;
            line-height: 1.8;
            margin: 0 0 1em 0;
        }}
        .summary-section p:last-child {{
            margin-bottom: 0;
        }}
        .summary-section ul {{
            margin: 0.5em 0 1em 1.5em;
            padding-left: 1.5em;
        }}
        .summary-section li {{
            margin-bottom: 0.4em;
            line-height: 1.6;
        }}
        
        .visualizations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin: 30px 0;
        }}
        
        .viz-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border: 2px solid #e0e0e0;
        }}
        
        .viz-card h3 {{
            color: #f5576c;
            font-size: 1.2em;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .viz-card img {{
            width: 100%;
            height: auto;
        }}
        .network-vis-wrapper {{
            position: relative;
            margin-top: 10px;
        }}
        .network-vis-wrapper canvas {{
            cursor: default;
        }}
        .network-enlarge-btn {{
            display: inline-block;
            margin-bottom: 10px;
            padding: 8px 16px;
            background: #f5576c;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        }}
        .network-enlarge-btn:hover {{
            background: #e04555;
        }}
        .network-enlarge-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 10000;
            justify-content: center;
            align-items: center;
        }}
        .network-enlarge-modal.is-open {{
            display: flex;
        }}
        .network-enlarge-modal .modal-content {{
            background: #fff;
            width: 90vw;
            height: 85vh;
            max-width: 1400px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .network-enlarge-modal .modal-header {{
            padding: 12px 20px;
            background: #f5576c;
            color: #fff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .network-enlarge-modal .modal-body {{
            flex: 1;
            min-height: 0;
        }}
        .network-enlarge-modal .modal-body .enlarge-network-container {{
            width: 100%;
            height: 100%;
            min-height: 400px;
        }}
        .network-enlarge-modal .modal-close {{
            background: #fff;
            color: #333;
            border: 1px solid #ccc;
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 4px;
        }}
        .images-full-size .viz-card {{
            overflow-x: auto;
        }}
        .images-full-size .viz-card img {{
            max-width: none;
            width: auto;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }}
        .images-full-size .debrief-recommendations-content {{
            overflow-x: auto;
        }}
        .images-full-size .debrief-recommendations-content img {{
            max-width: none;
            width: auto;
            height: auto;
            margin-left: auto;
            margin-right: auto;
        }}
        
        .tactics-summary {{
            background: #e8f5e9;
            padding: 20px;
            border-radius: 10px;
            margin: 25px 0;
            border-left: 5px solid #4caf50;
        }}
        
        .tactics-summary h3 {{
            color: #2e7d32;
            font-size: 1.3em;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .tactics-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 12px;
            margin-top: 15px;
        }}
        
        .tactic-item {{
            background: white;
            padding: 12px 15px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        .tactic-name {{
            font-weight: 500;
            color: #2d3436;
        }}
        
        .tactic-count {{
            background: #4caf50;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.9em;
        }}
        
        .debrief-recommendations-section {{
            background-color: #fcf8e3;
            padding: 25px;
            border-left: 5px solid #ffc107;
            border-radius: 8px;
            margin-top: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        
        .debrief-recommendations-section h2 {{
            color: #e0a800;
            font-size: 1.6em;
            margin-bottom: 20px;
            border-bottom: 2px solid #ffe082;
            padding-bottom: 10px;
        }}
        
        .debrief-recommendations-content {{
            font-size: 1em;
            line-height: 1.7;
            color: #333;
        }}
        
        .debrief-recommendations-content h1,
        .debrief-recommendations-content h2,
        .debrief-recommendations-content h3 {{
            color: #e0a800;
            border-bottom: 1px solid #ffe082;
            padding-bottom: 5px;
            margin-top: 20px;
            margin-bottom: 15px;
        }}
        
        .debrief-recommendations-content ul {{
            list-style-type: disc;
            margin-left: 20px;
            margin-bottom: 10px;
        }}
        
        .debrief-recommendations-content ol {{
            list-style-type: decimal;
            margin-left: 20px;
            margin-bottom: 10px;
        }}
        
        .debrief-recommendations-content li {{
            margin-bottom: 5px;
        }}
        
        .debrief-recommendations-content p {{
            margin-bottom: 10px;
        }}
        
        .debrief-recommendations-content pre {{
            background-color: #fff8dc;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            border: 1px solid #ffecb3;
        }}
        
        .debrief-recommendations-content code {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        .debrief-recommendations-content hr {{
            display: none;
        }}
        
        .debrief-recommendations-content img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #e0e0e0;
            margin: 20px auto;
            display: block;
            border-radius: 4px;
        }}
        
        .debrief-recommendations-content a {{
            color: #1976d2;
            text-decoration: none;
            border-bottom: 1px solid #1976d2;
        }}
        
        .debrief-recommendations-content a:hover {{
            color: #235AAA;
            border-bottom: 2px solid #235AAA;
        }}
        
        .debrief-recommendations-content .recommendation-meta {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            padding: 8px 14px;
            background: #fffde7;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }}
        .debrief-recommendations-content .recommendation-meta-label {{
            font-weight: 600;
            color: #5d4037;
        }}
        .debrief-recommendations-content .recommendation-meta-value {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
            background: #8d6e63;
            color: #fff;
        }}
        .debrief-recommendations-content .recommendation-meta-value.recommendation-criticality-critical {{
            background: #b71c1c;
            color: #fff;
        }}
        .debrief-recommendations-content .recommendation-meta-value.recommendation-criticality-high {{
            background: #e65100;
            color: #fff;
        }}
        .debrief-recommendations-content .recommendation-meta-value.recommendation-criticality-medium {{
            background: #f9a825;
            color: #1a1a1a;
        }}
        .debrief-recommendations-content .recommendation-meta-value.recommendation-criticality-low {{
            background: #2e7d32;
            color: #fff;
        }}
        
        .collapsible-recommendations-header {{
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .collapsible-recommendations-header:hover {{
            opacity: 0.9;
        }}
        .collapsible-toggle {{
            font-size: 0.85em;
            transition: transform 0.2s;
        }}
        .collapsible-recommendations-content.collapsed {{
            display: none;
        }}
        
        .data-summary {{
            background: #e3f2fd;
            padding: 20px;
            border-radius: 10px;
            margin: 25px 0;
            border-left: 5px solid #2196F3;
        }}
        
        .data-summary h3 {{
            color: #1976d2;
            font-size: 1.3em;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        
        .sheet-summary-item {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        .sheet-name {{
            font-weight: 600;
            color: #2d3436;
            font-size: 1.05em;
        }}
        
        .sheet-row-count {{
            color: #666;
            font-size: 0.95em;
        }}
        
        .debrief-footer {{
            background: #235AAA;
            color: white;
            padding: 20px;
            text-align: center;
            margin-top: 30px;
        }}
        
        .debrief-footer p {{
            margin: 5px 0;
            opacity: 0.9;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .debrief-header h1 {{
                font-size: 1.6em;
            }}
            .debrief-content {{
                padding: 20px;
            }}
            .quick-stats {{
                grid-template-columns: 1fr;
            }}
            .visualizations-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
{vis_network_script}
</head>
<body>
    <div class="{container_class_debrief}">{debrief_header_html}
        <div class="debrief-content">
            <!-- Quick Stats -->
            <div class="quick-stats">
                <div class="quick-stat-card">
                    <div class="quick-stat-value">{mitre_stats.get('total_detections', 0) if mitre_stats else 0}</div>
                    <div class="quick-stat-label">Total Detections</div>
                </div>
                <div class="quick-stat-card">
                    <div class="quick-stat-value">{mitre_stats.get('unique_tactics', 0) if mitre_stats else 0}</div>
                    <div class="quick-stat-label">Unique Tactics</div>
                </div>
                <div class="quick-stat-card">
                    <div class="quick-stat-value">{mitre_stats.get('unique_techniques', 0) if mitre_stats else 0}</div>
                    <div class="quick-stat-label">Techniques</div>
                </div>
                <div class="quick-stat-card">
                    <div class="quick-stat-value">{total_rows}</div>
                    <div class="quick-stat-label">Total Data Rows</div>
                </div>
            </div>
            
            {debrief_case_summary_section}
"""
        if mitre_stats and mitre_stats.get('tactics_count'):
            html += """
            <div class="tactics-summary">
                <h3>🎯 Top MITRE Tactics</h3>
                <div class="tactics-list">
"""
            for tactic, count in list(mitre_stats['tactics_count'].items())[:10]:
                html += f"""
                    <div class="tactic-item">
                        <span class="tactic-name">{tactic}</span>
                        <span class="tactic-count">{count}</span>
                    </div>
"""
            html += """
                </div>
            </div>
"""
        if timeline_img or network_img or network_data:
            html += """
            <div class="visualizations-grid">
"""
            if timeline_img:
                html += f"""
                <div class="viz-card">
                    <h3>⏱️ Timeline</h3>
                    <img src="{timeline_img}" alt="Incident Timeline" />
                </div>
"""
            if network_data:
                html += f"""
                <div class="viz-card">
                    <h3>🌐 Lateral Movement</h3>
                    <p style="margin-bottom:8px;font-size:0.9em;">Interactive: drag nodes, zoom and pan.</p>
                    <button type="button" class="network-enlarge-btn" id="network-enlarge-btn-debrief" aria-label="Enlarge network">Enlarge</button>
                    <div class="network-vis-wrapper">
                        <div id="network-vis-container-debrief" style="width:100%;height:480px;min-height:360px;"></div>
                    </div>
                    <div class="network-enlarge-modal" id="network-enlarge-modal-debrief" aria-hidden="true">
                        <div class="modal-content">
                            <div class="modal-header">
                                <span>Network Topology (enlarged)</span>
                                <button type="button" class="modal-close" id="network-enlarge-close-debrief">Close</button>
                            </div>
                            <div class="modal-body">
                                <div id="network-vis-enlarge-container-debrief" class="enlarge-network-container"></div>
                            </div>
                        </div>
                    </div>
                    <script>
(function() {{
    var networkData = {network_data_json};
    window._networkDataEnlargeDebrief = networkData;
    var container = document.getElementById('network-vis-container-debrief');
    var physicsOptions = {{ enabled: true, barnesHut: {{ springLength: 180, gravitationalConstant: -5000 }} }};
    var options = {{ physics: physicsOptions, nodes: {{ font: {{ size: 14 }} }} }};
    if (container && typeof vis !== 'undefined') {{
        var nodes = new vis.DataSet(networkData.nodes);
        var edges = new vis.DataSet(networkData.edges);
        var data = {{ nodes: nodes, edges: edges }};
        new vis.Network(container, data, options);
    }}
    var enlargeBtn = document.getElementById('network-enlarge-btn-debrief');
    var modal = document.getElementById('network-enlarge-modal-debrief');
    var closeBtn = document.getElementById('network-enlarge-close-debrief');
    var enlargeContainer = document.getElementById('network-vis-enlarge-container-debrief');
    var enlargeNetwork = null;
    function openEnlarge() {{
        if (typeof vis === 'undefined' || !window._networkDataEnlargeDebrief) return;
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        enlargeContainer.innerHTML = '';
        var nodes = new vis.DataSet(window._networkDataEnlargeDebrief.nodes);
        var edges = new vis.DataSet(window._networkDataEnlargeDebrief.edges);
        var data = {{ nodes: nodes, edges: edges }};
        enlargeNetwork = new vis.Network(enlargeContainer, data, options);
    }}
    function closeEnlarge() {{
        if (enlargeNetwork) {{ enlargeNetwork.destroy(); enlargeNetwork = null; }}
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
    }}
    if (enlargeBtn) enlargeBtn.addEventListener('click', openEnlarge);
    if (closeBtn) closeBtn.addEventListener('click', closeEnlarge);
    if (modal) modal.addEventListener('click', function(e) {{ if (e.target === modal) closeEnlarge(); }});
}})();
                    </script>
                </div>
"""
            elif network_img:
                html += f"""
                <div class="viz-card">
                    <h3>🌐 Lateral Movement</h3>
                    <img src="{network_img}" alt="Lateral Movement" />
                </div>
"""
            html += """
            </div>
"""
        
        if investigation_summary_content:
            investigation_content_without_case_summary = self.strip_markdown_section(
                investigation_summary_content, "Case Summary"
            )
            investigation_content_without_case_summary = self.strip_markdown_section(
                investigation_content_without_case_summary, "Diamond Model"
            )
            html += """
            <div class="debrief-recommendations-section" style="background-color: #e3f2fd; border-left: 5px solid #2196F3; margin-top: 30px;">
                <h2 style="color: #1976d2;">Investigation Summary</h2>
                <div class="debrief-recommendations-content">
"""
            html += self.convert_markdown_to_html(
                investigation_content_without_case_summary, investigation_summary_file_path
            )
            
            html += """
                </div>
            </div>
"""
        if recommendations_content:
            recommendations_content = self.sort_recommendations_by_criticality(recommendations_content)
            html += """
            <div class="debrief-recommendations-section collapsible-recommendations" style="margin-top: 30px;">
                <h2 class="collapsible-recommendations-header">
                    <span class="collapsible-toggle" aria-hidden="true">▶</span>
                    Recommendations
                </h2>
                <div class="debrief-recommendations-content collapsible-recommendations-content collapsed">
"""
            html += self.convert_markdown_to_html(recommendations_content, recommendations_file_path)
            html += """
                </div>
            </div>
"""
        if report_data.get("sheets"):
            html += """
            <div class="data-summary">
                <h3>📊 Data Summary</h3>
"""
            for sheet_name, sheet_data in report_data.get("sheets", {}).items():
                if sheet_name == config.SHEET_TIMELINE:
                    continue
                row_count = len(sheet_data.get('data', []))
                display_name = self.get_sheet_display_name(sheet_name)
                html += f"""
                <div class="sheet-summary-item">
                    <span class="sheet-name">{display_name}</span>
                    <span class="sheet-row-count">{row_count} rows</span>
                </div>
"""
            html += """
            </div>
"""
        
        html += f"""
        </div>
        {debrief_footer_html}
    </div>
    <script>
    document.querySelectorAll('.collapsible-recommendations-header').forEach(function(h, idx) {{
        var content = h.nextElementSibling;
        var toggle = h.querySelector('.collapsible-toggle');
        if (!content || !toggle) return;
        if (!content.id) content.id = 'collapsible-content-' + idx;
        h.setAttribute('role', 'button');
        h.setAttribute('tabindex', '0');
        h.setAttribute('aria-expanded', content.classList.contains('collapsed') ? 'false' : 'true');
        h.setAttribute('aria-controls', content.id);
        function toggleContent() {{
            content.classList.toggle('collapsed');
            toggle.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
            h.setAttribute('aria-expanded', content.classList.contains('collapsed') ? 'false' : 'true');
        }}
        h.addEventListener('click', toggleContent);
        h.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' || e.key === ' ') {{
                e.preventDefault();
                toggleContent();
            }}
        }});
    }});
    </script>
</body>
</html>
"""
        
        html = html.replace("#235AAA", report_color)
        html = html.replace("#c62828", report_color)
        return html
