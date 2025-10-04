# code reviewed 
from PySide6.QtWidgets import QProgressBar, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import QThread, Signal, QObject
import requests
import sqlite3
import csv
import json
import os
import pandas as pd
from pathlib import Path
import logging
import zipfile
import shutil

logger = logging.getLogger(__name__)

class DownloadWorker(QObject):
    progress = Signal(int)
    status_update = Signal(str)
    finished = Signal(bool, str)
    file_progress = Signal(int, int)
    
    def __init__(self, db_path, urls, headers):
        super().__init__()
        self.db_path = db_path
        self.urls = urls
        self.headers = headers
        self.should_cancel = False
    def cancel(self):
        self.should_cancel = True
    def run(self):
        try:
            downloaded_files = []
            total_steps = len(self.urls) + 1
            current_step = 0
            for i, (filename, url) in enumerate(self.urls.items(), start=1):
                if self.should_cancel:
                    self.status_update.emit("Download cancelled by user")
                    self.finished.emit(False, "Download cancelled")
                    return
                self.file_progress.emit(i, len(self.urls))
                self.status_update.emit(f"Downloading {filename}...")
                try:
                    response = requests.get(url, headers=self.headers, stream=True, timeout=30)
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    with open(filename, "wb") as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self.should_cancel:
                                file.close()
                                os.remove(filename)
                                self.finished.emit(False, "Download cancelled")
                                return
                            file.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                file_progress = int((downloaded_size / total_size) * 100)
                                overall_progress = int(((current_step + file_progress/100) / total_steps) * 100)
                                self.progress.emit(overall_progress)
                    downloaded_files.append(filename)
                except Exception as e:
                    logger.error(f"Failed to download {filename}: {e}")
                    self.status_update.emit(f"Failed to download {filename}: {str(e)}")
                current_step += 1
                progress_value = int((current_step / total_steps) * 100)
                self.progress.emit(progress_value)
            if self.should_cancel:
                self.finished.emit(False, "Download cancelled")
                return
            self.status_update.emit("Updating database...")
            self.update_database()
            self.status_update.emit("Processing LOLBAS files...")
            self.process_lolbas_zip()
            self.status_update.emit("Cleaning up temporary files...")
            self.cleanup_files(downloaded_files)
            self.progress.emit(100)
            self.status_update.emit("Complete!")
            self.finished.emit(True, "All updates downloaded and database updated successfully!")
        except Exception as e:
            logger.error(f"Error in download worker: {e}")
            self.finished.emit(False, f"Error: {str(e)}")
    def update_database(self):
        def insert_portal_data(cursor, group_name, portal_name, primary_url, source_file):
            cursor.execute('''
                INSERT INTO ms_portals (group_name, portal_name, primary_url, source_file)
                VALUES (?, ?, ?, ?)
            ''', (group_name, portal_name, primary_url, source_file))
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tor_list")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='tor_list'")
            def insert_data(file_name, source):
                try:
                    with open(file_name, "r") as file:
                        for line in file:
                            ip_address = line.strip()
                            if ip_address:
                                cursor.execute(
                                    "INSERT OR IGNORE INTO tor_list (ipaddress_, insert_date, source) VALUES (?, DATE('now'), ?)",
                                    (ip_address, source),
                                )
                except FileNotFoundError:
                    logger.error(f"File {file_name} not found.")
                except Exception as e:
                    logger.error(f"Error processing {file_name}: {e}")
            insert_data("dan.txt", "dan.txt")
            insert_data("torproject.txt", "torproject.txt")
            insert_data("secureupdates.txt", "secureupdates.txt")
            cursor.execute("DELETE FROM cisa_ran_exploit")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='cisa_ran_exploit'")
            cisa_csv = Path("known_exploited_vulnerabilities.csv")
            cisa_columns = ['cveID', 'vendorProject', 'product', 'knownRansomwareCampaignUse']
            if cisa_csv.exists():
                try:
                    df_cisa = pd.read_csv(cisa_csv, dtype=str)
                    for col in cisa_columns:
                        if col not in df_cisa.columns:
                            df_cisa[col] = ""
                    df_cisa = df_cisa[cisa_columns]
                    for _, row in df_cisa.iterrows():
                        cursor.execute('''
                            INSERT INTO cisa_ran_exploit (cveID, vendorProject, product, knownRansomwareCampaignUse)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            row['cveID'],
                            row['vendorProject'],
                            row['product'],
                            row['knownRansomwareCampaignUse']
                        ))
                except Exception as e:
                    logger.error(f"Error processing {cisa_csv}: {e}")
            cursor.execute("DELETE FROM evtx_id")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='evtx_id'")
            evtx_file = Path("evtx_id.csv")
            if evtx_file.exists():
                with open(evtx_file, "r", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        cursor.execute('''
                            INSERT INTO evtx_id (category, event_id, description, Provider)
                            VALUES (?, ?, ?, ?)
                        ''', (row.get("category", ""), row.get("event_id", ""), row.get("description", ""), row.get("Provider", "")))
            cursor.execute("DELETE FROM mitre_techniques")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='mitre_techniques'")
            with open("mitre_techniques.csv", "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    cursor.execute('''
                        INSERT INTO mitre_techniques (PID, ID, Name)
                        VALUES (?, ?, ?)
                    ''', (row.get("PID", ""), row.get("ID", ""), row.get("Name", "")))
            cursor.execute("DELETE FROM ms_portals")
            json_files = [
                'user.json',
                'thirdparty.json',
                'us-govt.json',
                'china.json',
                'admin.json',
                'licensing.json'
            ]
            for json_file in json_files:
                file_path = Path(json_file)
                if not file_path.exists():
                    logger.warning(f"File {json_file} does not exist, skipping.")
                    continue
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    for group in data:
                        group_name = group.get('groupName')
                        for portal in group.get('portals', []):
                            portal_name = portal.get('portalName')
                            primary_url = portal.get('primaryURL')
                            if not all([group_name, portal_name, primary_url]):
                                continue
                            insert_portal_data(cursor, group_name, portal_name, primary_url, file_path.name)
                except Exception as e:
                    logger.error(f"Error processing {json_file}: {e}")
            cursor.execute("DELETE FROM entra_appid")
            csv_files = [
                'MicrosoftApps.csv',
                'Malicious_EntraID.csv'
            ]
            expected_columns = ['AppId', 'AppDisplayName', 'AppOwnerOrganizationId', 'Source']
            for file in csv_files:
                file_path = Path(file)
                if not file_path.exists():
                    logger.warning(f"File {file} does not exist, skipping.")
                    continue
                try:
                    df = pd.read_csv(file_path, dtype=str)
                    for col in expected_columns:
                        if col not in df.columns:
                            df[col] = ""
                    df = df[expected_columns]
                    df['FileName'] = file_path.name
                    for _, row in df.iterrows():
                        cursor.execute('''
                            INSERT INTO entra_appid (AppId, AppDisplayName, AppOwnerOrganizationId, Source, FileName)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            row['AppId'],
                            row['AppDisplayName'],
                            row['AppOwnerOrganizationId'],
                            row['Source'],
                            row['FileName']
                        ))
                except Exception as e:
                    logger.error(f"Error processing {file}: {e}")
            cursor.execute("DELETE FROM bookmarks WHERE group_name != 'Personal'")
            onetracker_csv = Path("onetracker.csv")
            bookmarks_columns = ['group_name', 'portal_name', 'source_file', 'primary_url']
            if onetracker_csv.exists():
                try:
                    df_bookmarks = pd.read_csv(onetracker_csv, dtype=str)
                    for col in bookmarks_columns:
                        if col not in df_bookmarks.columns:
                            df_bookmarks[col] = ""
                    df_bookmarks = df_bookmarks[bookmarks_columns]
                    for _, row in df_bookmarks.iterrows():
                        cursor.execute("SELECT COUNT(*) FROM bookmarks WHERE primary_url = ?", (row['primary_url'],))
                        if cursor.fetchone()[0] == 0:
                            cursor.execute('''
                                INSERT INTO bookmarks (group_name, portal_name, source_file, primary_url)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                row['group_name'],
                                row['portal_name'],
                                row['source_file'],
                                row['primary_url']
                            ))
                except Exception as e:
                    logger.error(f"Error processing {onetracker_csv}: {e}")
            else:
                logger.warning(f"File {onetracker_csv} does not exist, skipping.")
            cursor.execute("DELETE FROM bookmarks WHERE portal_name = 'PlaceHolder' AND id NOT IN (SELECT MIN(id) FROM bookmarks WHERE portal_name = 'PlaceHolder')")
            cursor.execute("DELETE FROM defend")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='defend'")
            d3fend_csv = Path("d3fend-full-mappings.csv")
            if d3fend_csv.exists():
                try:
                    df_d3fend = pd.read_csv(d3fend_csv, dtype=str)
                    for _, row in df_d3fend.iterrows():
                        cursor.execute('''
                            INSERT INTO defend ({cols})
                            VALUES ({placeholders})
                        '''.format(
                            cols=", ".join([f'"{col}"' for col in df_d3fend.columns]),
                            placeholders=", ".join(["?"] * len(df_d3fend.columns))
                        ), tuple(row[col] for col in df_d3fend.columns))
                except Exception as e:
                    logger.error(f"Error processing {d3fend_csv}: {e}")
            else:
                logger.warning(f"File {d3fend_csv} does not exist, skipping.")
            cursor.execute("DELETE FROM EvidenceType")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='EvidenceType'")
            evidencetype_csv = Path("evidencetype.csv")
            if evidencetype_csv.exists():
                try:
                    with open(evidencetype_csv, "r", encoding="utf-8") as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            cursor.execute('''
                                INSERT INTO EvidenceType (evidencetype, sort_order, source)
                                VALUES (?, ?, ?)
                            ''', (row.get("evidencetype", ""), row.get("sort_order", ""), row.get("source", "")))
                except Exception as e:
                    logger.error(f"Error processing {evidencetype_csv}: {e}")
            else:
                logger.warning(f"File {evidencetype_csv} does not exist, skipping.")
            conn.commit()
            logger.info("Database updated successfully.")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    def process_lolbas_zip(self):
        zip_file = Path("lolbas_binaries.zip")
        if not zip_file.exists():
            logger.warning(f"LOLBAS zip file {zip_file} does not exist, skipping.")
            return
        
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            lolbas_dir = data_dir / "lolbas"
            if lolbas_dir.exists():
                logger.info(f"Deleting existing LOLBAS directory: {lolbas_dir}")
                shutil.rmtree(lolbas_dir)
            lolbas_dir.mkdir(exist_ok=True)
            logger.info(f"Extracting {zip_file} to {lolbas_dir}")
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(lolbas_dir)
                yml_files = list(lolbas_dir.rglob("*.yml"))
                logger.info(f"Successfully extracted {len(yml_files)} .yml files to {lolbas_dir}")
        except Exception as e:
            logger.error(f"Error processing LOLBAS zip file: {e}")
    def cleanup_files(self, file_list):
        for file_to_delete in file_list:
            try:
                if os.path.exists(file_to_delete):
                    os.remove(file_to_delete)
                    logger.info(f"Deleted file: {file_to_delete}")
            except OSError as e:
                logger.error(f"Error deleting file {file_to_delete}: {e}")
class DownloadProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Updates")
        self.setModal(True)
        self.setFixedSize(450, 150)
        self.worker = None
        self.thread = None
        if parent:
            parent_rect = parent.geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2
            )
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Preparing to download...")
        layout.addWidget(self.status_label)
        self.file_label = QLabel("File 0 of 0")
        layout.addWidget(self.file_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_download)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    def start_download(self, db_path, urls, headers):
        self.thread = QThread()
        self.worker = DownloadWorker(db_path, urls, headers)
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.file_progress.connect(self.update_file_progress)
        self.worker.finished.connect(self.download_finished)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
    def update_file_progress(self, current_file, total_files):
        self.file_label.setText(f"File {current_file} of {total_files}")
    def cancel_download(self):
        if self.worker:
            self.worker.cancel()
            self.cancel_button.setText("Cancelling...")
            self.cancel_button.setEnabled(False)
    def download_finished(self, success, message):
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Download Complete" if success else "Download Failed")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information if success else QMessageBox.Warning)
        msg_box.exec()
        self.accept() if success else self.reject()
def download_updates(window):
    urls = {
        "alireza-rezaee.csv": "https://raw.githubusercontent.com/alireza-rezaee/tor-nodes/main/latest.all.csv",
        "torproject.txt": "https://check.torproject.org/torbulkexitlist",
        "d3fend-full-mappings.csv": "https://d3fend.mitre.org/api/ontology/inference/d3fend-full-mappings.csv",
        "user.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/user.json",
        "admin.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/admin.json",
        "thirdparty.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/thirdparty.json",
        "us-govt.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/us-govt.json",
        "china.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/china.json",
        "edu.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/edu.json",
        "licensing.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/licensing.json",
        "training.json": "https://raw.githubusercontent.com/adamfowlerit/msportals.io/refs/heads/master/_data/portals/training.json",
        "evtx_id.csv": "https://raw.githubusercontent.com/arimboor/lookups/refs/heads/main/evtx_id.csv",
        "mitre_techniques.csv": "https://raw.githubusercontent.com/arimboor/lookups/refs/heads/main/mitre_techniques_v17.csv",
        "known_exploited_vulnerabilities.csv": "https://www.cisa.gov/sites/default/files/csv/known_exploited_vulnerabilities.csv",
        "MicrosoftApps.csv": "https://raw.githubusercontent.com/merill/microsoft-info/main/_info/MicrosoftApps.csv",
        "GraphAppRoles.csv": "https://raw.githubusercontent.com/merill/microsoft-info/main/_info/GraphAppRoles.csv",
        "GraphDelegateRoles.csv": "https://raw.githubusercontent.com/merill/microsoft-info/main/_info/GraphDelegateRoles.csv",
        "Malicious_EntraID.csv": "https://raw.githubusercontent.com/arimboor/lookups/refs/heads/main/Malicious_EntraID.csv",
        "onetracker.csv": "https://raw.githubusercontent.com/arimboor/lookups/refs/heads/main/onetracker.csv",
        "evidencetype.csv": "https://raw.githubusercontent.com/arimboor/lookups/refs/heads/main/evidencetype.csv",
        "secureupdates.txt": "https://secureupdates.checkpoint.com/IP-list/TOR.txt",
        "lolbas_binaries.zip": "https://raw.githubusercontent.com/arimboor/kanvas_lookups/main/lolbas_binaries.zip",
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    db_path = getattr(window, "db_path", "kanvas.db")
    dialog = DownloadProgressDialog(window)
    dialog.start_download(db_path, urls, headers)
    dialog.exec()