# code Reviewed 
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, 
    QPushButton, QScrollArea, QFileDialog, QCheckBox
)
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap
from PySide6.QtCore import Qt, QRect, QSizeF
from datetime import datetime
import csv
import traceback
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

from helper import config, styles

def open_timeline_window(window):
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
            logger.error(f"Failed to read sheet headers: {str(e)}\n{traceback.format_exc()}")
            return None
        try:
            dt_col = headers.index(config.COL_TIMESTAMP)
            desc_col = headers.index(config.COL_ACTIVITY)
            mitre_col = headers.index(config.COL_MITRE_TACTIC)
            event_sys_col = headers.index(config.COL_EVENT_SYSTEM) if config.COL_EVENT_SYSTEM in headers else None
            visualize_col = headers.index(config.COL_VISUALIZE) if config.COL_VISUALIZE in headers else None
        except ValueError as e:
            QMessageBox.critical(window, "Error", f"Required columns '{config.COL_TIMESTAMP}', '{config.COL_ACTIVITY}', and/or '{config.COL_MITRE_TACTIC}' not found.")
            logger.error(f"Required column not found: {str(e)}")
            return None
        timeline_activities = []
        skipped_rows = 0
        try:
            for row_idx in range(2, sheet.max_row + 1):
                try:
                    dt_val = sheet.cell(row=row_idx, column=dt_col+1).value
                    desc_val = sheet.cell(row=row_idx, column=desc_col+1).value
                    mitre_val = sheet.cell(row=row_idx, column=mitre_col+1).value
                    event_sys_val = sheet.cell(row=row_idx, column=event_sys_col+1).value if event_sys_col is not None else ""
                    visualize_val = sheet.cell(row=row_idx, column=visualize_col+1).value if visualize_col is not None else config.VAL_VISUALIZE_YES.capitalize()
                    if isinstance(visualize_val, str):
                        visualize_val = visualize_val.strip()
                    if visualize_val.lower() != config.VAL_VISUALIZE_YES:
                        continue
                    if isinstance(dt_val, str):
                        dt_val = dt_val.strip()
                    if isinstance(desc_val, str):
                        desc_val = desc_val.strip()
                    if isinstance(mitre_val, str):
                        mitre_val = mitre_val.strip()
                    if isinstance(event_sys_val, str):
                        event_sys_val = event_sys_val.strip()
                    if dt_val and desc_val and mitre_val:
                        if isinstance(dt_val, datetime):
                            activity_datetime = dt_val
                        else:
                            try:
                                try:
                                    activity_datetime = datetime.strptime(str(dt_val), "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    try:
                                        activity_datetime = datetime.strptime(str(dt_val), "%Y-%m-%d")
                                    except ValueError as e:
                                        logger.warning(f"Row {row_idx}: Could not parse date '{dt_val}' with standard formats, skipping: {str(e)}")
                                        skipped_rows += 1
                                        continue
                            except Exception as e:
                                logger.warning(f"Row {row_idx}: Invalid date '{dt_val}' ({str(e)})")
                                skipped_rows += 1
                                continue
                        timeline_activities.append((activity_datetime, str(desc_val), str(mitre_val), str(event_sys_val)))
                    else:
                        logger.warning(f"Row {row_idx}: Missing required data - date='{dt_val}', activity='{desc_val}', MITRE Tactic='{mitre_val}'")
                        skipped_rows += 1
                except Exception as e:
                    logger.error(f"Error processing row {row_idx}: {str(e)}")
                    skipped_rows += 1
                    continue
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Failed to process timeline data: {str(e)}")
            logger.error(f"Failed to process timeline data: {str(e)}\n{traceback.format_exc()}")
            return None
        if not timeline_activities:
            QMessageBox.warning(window, "Warning", "No valid timeline entries found after processing.")
            return None
        timeline_activities.sort(key=lambda x: x[0])
        try:
            timeline_window = QWidget(window)
            timeline_window.setWindowTitle("Incident Timeline")
            timeline_window.resize(1100, 800)
            timeline_window.setWindowFlags(Qt.Window | Qt.WindowTitleHint | 
                                          Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | 
                                          Qt.WindowMaximizeButtonHint)
            main_layout = QVBoxLayout()
            header_panel = QHBoxLayout()
            header_label = QLabel("Incident Timeline")
            header_label.setStyleSheet(styles.LABEL_TITLE_STYLE)
            header_label.setAlignment(Qt.AlignLeft)
            header_panel.addWidget(header_label, 1)
            checkbox_layout = QHBoxLayout()
            day_wise_cb = QCheckBox("Day-wise")
            event_system_cb = QCheckBox("Event System")
            checkbox_layout.addWidget(day_wise_cb)
            checkbox_layout.addWidget(event_system_cb)
            header_panel.addLayout(checkbox_layout)
            export_layout = QHBoxLayout()
            export_label = QLabel("Export as:")
            export_layout.addWidget(export_label)
            export_png_btn = QPushButton("PNG")
            export_png_btn.setStyleSheet(styles.BUTTON_STYLE_BASE)
            export_csv_btn = QPushButton("CSV")
            export_csv_btn.setStyleSheet(styles.BUTTON_STYLE_SECONDARY)
            export_layout.addWidget(export_png_btn)
            export_layout.addWidget(export_csv_btn)
            header_panel.addLayout(export_layout)
            main_layout.addLayout(header_panel)
            status_bar = QLabel("")
            status_bar.setStyleSheet(styles.STATUS_BAR_TEXT_STYLE)
            main_layout.addWidget(status_bar)
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Failed to create UI components: {str(e)}")
            logger.error(f"Failed to create UI components: {str(e)}\n{traceback.format_exc()}")
            return None
        class TimelineCanvas(QWidget):
            def __init__(self, activities, show_event_system=False, day_wise=False):
                super().__init__()
                self.activities = activities
                self.show_event_system = show_event_system
                self.day_wise = day_wise
                self.margin = 50
                self.line_x = 400
                self.marker_size = 7
                self.min_spacing = 100 
                self.setMinimumSize(800, max(1000, len(activities) * self.min_spacing + 2 * self.margin))
                self.setAutoFillBackground(True)
                palette = self.palette()
                palette.setColor(self.backgroundRole(), QColor("white"))
                self.setPalette(palette)
                
            def calculateTextHeight(self, painter, text, width):
                rect = QRect(0, 0, width, 1000)  
                boundingRect = painter.boundingRect(rect, Qt.TextWordWrap | Qt.AlignLeft, text)
                return boundingRect.height()
                
            def paintEvent(self, event):
                try:
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.fillRect(self.rect(), QColor("white"))
                    if not self.activities:
                        return
                    canvas_width = self.width()
                    canvas_height = max(1000, len(self.activities) * self.min_spacing + 2 * self.margin)
                    desc_width = 550
                    text_offset = 20
                    activity_heights = []
                    for activity in self.activities:
                        desc = activity[1]
                        event_system = activity[3] if len(activity) > 3 else ""
                        painter.setFont(QFont("Arial", 10))
                        height = 30  
                        if self.show_event_system and event_system:
                            height += 20
                        desc_height = self.calculateTextHeight(painter, desc, desc_width) + 10  
                        height += desc_height
                        activity_heights.append(max(height, 60))
                    min_date = min(self.activities, key=lambda x: x[0])[0]
                    max_date = max(self.activities, key=lambda x: x[0])[0]
                    time_range = (max_date - min_date).total_seconds()
                    if time_range == 0:
                        time_range = 1
                    y_positions = [self.margin]  
                    for i in range(1, len(self.activities)):
                        prev_y = y_positions[-1]
                        current_y = prev_y + activity_heights[i-1] + 20  
                        y_positions.append(current_y)
                    line_start = y_positions[0]
                    line_end = y_positions[-1] + activity_heights[-1]
                    painter.setPen(QPen(QColor("black"), 2))
                    painter.drawLine(self.line_x, line_start, self.line_x, line_end)
                    current_day = None
                    day_count = 0
                    for i, (y_pos, activity) in enumerate(zip(y_positions, self.activities)):
                        date = activity[0]
                        desc = activity[1]
                        mitre = activity[2]
                        event_system = activity[3] if len(activity) > 3 else ""
                        activity_day = date.date()
                        if self.day_wise and activity_day != current_day:
                            current_day = activity_day
                            day_count += 1
                            painter.setPen(QPen(QColor("darkblue")))
                            painter.setFont(QFont("Arial", 11, QFont.Bold))
                            painter.drawText(
                                QRect(self.line_x - 200 - text_offset, y_pos - 30, 200, 20),
                                Qt.AlignRight | Qt.AlignVCenter,
                                f"Day {day_count}"
                            )
                        painter.setBrush(QBrush(QColor("blue")))
                        painter.drawEllipse(
                            self.line_x - self.marker_size,
                            y_pos - self.marker_size,
                            self.marker_size * 2,
                            self.marker_size * 2
                        )
                        timestamp_str = date.strftime("%Y-%m-%d %H:%M:%S")
                        painter.setPen(QPen(QColor("red")))
                        painter.setFont(QFont("Arial", 10, QFont.Bold))
                        painter.drawText(
                            QRect(self.line_x - 200 - text_offset, y_pos - 10, 200, 20),
                            Qt.AlignRight | Qt.AlignVCenter,
                            timestamp_str
                        )
                        painter.setPen(QPen(Qt.NoPen))
                        mitre_rect = QRect(self.line_x + text_offset, y_pos - 10, 325, 20) 
                        painter.setBrush(QBrush(QColor("darkorange")))
                        painter.drawRect(mitre_rect)
                        painter.setPen(QPen(QColor("white")))
                        painter.drawText(mitre_rect, Qt.AlignLeft | Qt.AlignVCenter, mitre)
                        current_y_offset = 15
                        if self.show_event_system and event_system:
                            painter.setFont(QFont("Arial", 9, QFont.Bold))
                            painter.setPen(QPen(QColor("darkgreen")))
                            painter.drawText(
                                QRect(self.line_x + text_offset, y_pos + current_y_offset, desc_width, 20),
                                Qt.AlignLeft,
                                f"System: {event_system}"
                            )
                            current_y_offset += 20
                        painter.setPen(QPen(QColor("black")))
                        painter.setFont(QFont("Arial", 10))
                        desc_height = self.calculateTextHeight(painter, desc, desc_width)
                        desc_rect = QRect(self.line_x + text_offset, y_pos + current_y_offset, desc_width, desc_height + 10)
                        painter.drawText(
                            desc_rect,
                            Qt.TextWordWrap | Qt.AlignLeft,
                            desc
                        )
                    new_height = int(y_positions[-1] + activity_heights[-1] + self.margin)
                    if new_height > self.height():
                        self.setMinimumHeight(new_height)
                except Exception as e:
                    logger.error(f"Error in paintEvent: {str(e)}\n{traceback.format_exc()}")
                    painter = QPainter(self)
                    painter.fillRect(self.rect(), QColor("white"))
                    painter.setPen(QPen(QColor("red")))
                    painter.setFont(QFont("Arial", 12))
                    painter.drawText(
                        self.rect(),
                        Qt.AlignCenter,
                        f"Error rendering timeline: {str(e)}"
                    )
        try:
            timeline_canvas = TimelineCanvas(timeline_activities, False)
            scroll_area = QScrollArea()
            scroll_area.setWidget(timeline_canvas)
            scroll_area.setWidgetResizable(True)
            main_layout.addWidget(scroll_area)
            
            def update_timeline_display():
                try:
                    show_event_system = event_system_cb.isChecked()
                    show_day_wise = day_wise_cb.isChecked()
                    new_timeline = TimelineCanvas(timeline_activities, show_event_system, show_day_wise)
                    scroll_area.setWidget(new_timeline)
                except Exception as e:
                    status_bar.setText(f"Error updating timeline: {str(e)}")
                    logger.error(f"Error updating timeline: {str(e)}\n{traceback.format_exc()}")
                    QMessageBox.warning(timeline_window, "Update Error", f"Failed to update timeline: {str(e)}")
            
            day_wise_cb.toggled.connect(update_timeline_display)
            event_system_cb.toggled.connect(update_timeline_display)
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Failed to create timeline canvas: {str(e)}")
            logger.error(f"Failed to create timeline canvas: {str(e)}\n{traceback.format_exc()}")
            return None
        
        def export_to_png():
            try:
                file_path, _ = QFileDialog.getSaveFileName(
                    timeline_window,
                    "Export Timeline to PNG",
                    f"Timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    "PNG Files (*.png)"
                )
                if not file_path:
                    return
                status_bar.setText("Exporting to PNG...")
                timeline_window.repaint()
                current_canvas = scroll_area.widget()
                size = current_canvas.size()
                if size.width() <= 0 or size.height() <= 0:
                    raise ValueError("Invalid canvas size for export")
                pixmap = QPixmap(size)
                pixmap.fill(Qt.white)
                current_canvas.render(pixmap)
                if pixmap.save(file_path, "PNG"):
                    status_bar.setText(f"Timeline exported to PNG: {file_path}")
                    logger.info(f"Timeline exported to PNG: {file_path}")
                    QMessageBox.information(timeline_window, "Export Complete", f"Timeline exported to PNG: {file_path}")
                else:
                    raise Exception("Failed to save PNG file")
            except Exception as e:
                error_msg = f"PNG export failed: {str(e)}"
                status_bar.setText(error_msg)
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                QMessageBox.critical(timeline_window, "Export Error", f"Failed to export to PNG: {str(e)}")
        
        def export_to_csv():
            try:
                file_path, _ = QFileDialog.getSaveFileName(
                    timeline_window,
                    "Export Timeline to CSV",
                    f"Timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "CSV Files (*.csv)"
                )
                if not file_path:
                    return
                status_bar.setText("Exporting to CSV...")
                timeline_window.repaint()
                with open(file_path, 'w', newline='', encoding='utf-8') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow([config.COL_TIMESTAMP, config.COL_MITRE_TACTIC, config.COL_EVENT_SYSTEM, config.COL_ACTIVITY])
                    for timestamp, activity, mitre, event_system in timeline_activities:
                        csv_writer.writerow([timestamp.strftime('%Y-%m-%d %H:%M:%S'), mitre, event_system, activity])
                status_bar.setText(f"Timeline exported to CSV: {file_path}")
                QMessageBox.information(timeline_window, "Export Complete", f"Timeline exported to CSV: {file_path}")
            except PermissionError:
                error_msg = f"Permission denied when writing to {file_path}"
                status_bar.setText(error_msg)
                logger.error(error_msg)
                QMessageBox.critical(timeline_window, "Export Error", f"Permission denied. The file may be in use or you don't have write permission.")
            except Exception as e:
                error_msg = f"CSV export failed: {str(e)}"
                status_bar.setText(error_msg)
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                QMessageBox.critical(timeline_window, "Export Error", f"Failed to export to CSV: {str(e)}")
        export_png_btn.clicked.connect(export_to_png)
        export_csv_btn.clicked.connect(export_to_csv)
        timeline_window.setLayout(main_layout)
        timeline_window.show()
        return timeline_window
        
    except Exception as e:
        logger.error(f"Unhandled exception in open_timeline_window: {str(e)}\n{traceback.format_exc()}")
        QMessageBox.critical(window, "Error", f"An unexpected error occurred: {str(e)}")
        return None