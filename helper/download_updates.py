# download_updates.py: fetches external data (Tor, CISA, portals, LOLBAS, artifacts,
# HijackLibs, SID, LOLESXi, LOLDrivers, etc.) from URLs defined in helper/download_links.yaml,
# updates the SQLite database, and extracts archives into data/ for use by the application.
# Revised on 01/02/2026 by Jinto Antony

import csv
import json
import logging
import os
import shutil
import sqlite3
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests
import yaml
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)

DOWNLOAD_LINKS_YAML = "download_links.yaml"


def load_download_urls():
    base_dir = Path(__file__).resolve().parent
    yaml_path = base_dir / DOWNLOAD_LINKS_YAML
    if not yaml_path.is_file():
        logger.warning("download_links.yaml not found at %s", yaml_path)
        return {}
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if not data or not isinstance(data, dict):
            logger.warning("download_links.yaml empty or invalid")
            return {}
        return {str(k): str(v) for k, v in data.items() if v}
    except Exception as e:
        logger.warning("Could not load download_links.yaml: %s", e)
        return {}


def handle_remove_readonly(func, path, exc):
    try:
        os.chmod(path, 0o777)
        func(path)
    except Exception:
        try:
            func(path)
        except Exception:
            pass


def remove_tree_safe(path, retry_delay=0.2):
    if not path or not path.exists():
        return
    try:
        shutil.rmtree(path, onerror=handle_remove_readonly)
    except Exception as e:
        logger.warning("Could not remove directory %s: %s", path, e)
        time.sleep(retry_delay)
        try:
            shutil.rmtree(path, onerror=handle_remove_readonly)
        except Exception as e2:
            logger.error("Failed to remove directory after retry: %s", e2)

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
                    logger.error("Failed to download %s: %s", filename, e)
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
            self.status_update.emit("Processing artifacts files...")
            self.process_artifacts_zip()
            self.status_update.emit("Processing HijackLibs files...")
            self.process_hijacklibs_zip()
            self.status_update.emit("Processing SID file...")
            self.process_sid_file()
            self.status_update.emit("Processing LOLESXi files...")
            self.process_lolesxi_zip()
            self.status_update.emit("Processing drivers file...")
            self.process_drivers_file()
            self.status_update.emit("Cleaning up temporary files...")
            self.cleanup_files(downloaded_files)
            self.progress.emit(100)
            self.status_update.emit("Complete!")
            self.finished.emit(True, "All updates downloaded and database updated successfully!")
        except Exception as e:
            logger.error("Error in download worker: %s", e)
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
                    logger.error("File %s not found.", file_name)
                except Exception as e:
                    logger.error("Error processing %s: %s", file_name, e)
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
                    logger.error("Error processing %s: %s", cisa_csv, e)
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
                    logger.warning("File %s does not exist, skipping.", json_file)
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
                    logger.error("Error processing %s: %s", json_file, e)
            cursor.execute("DELETE FROM entra_appid")
            csv_files = [
                'MicrosoftApps.csv',
                'Malicious_EntraID.csv'
            ]
            expected_columns = ['AppId', 'AppDisplayName', 'AppOwnerOrganizationId', 'Source']
            for file in csv_files:
                file_path = Path(file)
                if not file_path.exists():
                    logger.warning("File %s does not exist, skipping.", file)
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
                    logger.error("Error processing %s: %s", file, e)
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
                    logger.error("Error processing %s: %s", onetracker_csv, e)
            else:
                logger.warning("File %s does not exist, skipping.", onetracker_csv)
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
                    logger.error("Error processing %s: %s", d3fend_csv, e)
            else:
                logger.warning("File %s does not exist, skipping.", d3fend_csv)
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
                    logger.error("Error processing %s: %s", evidencetype_csv, e)
            else:
                logger.warning("File %s does not exist, skipping.", evidencetype_csv)
            conn.commit()
            logger.info("Database updated successfully.")
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            raise
        finally:
            if conn:
                conn.close()
    def process_lolbas_zip(self):
        zip_file = Path("lolbas_binaries.zip")
        if not zip_file.exists():
            logger.warning("LOLBAS zip file %s does not exist, skipping.", zip_file)
            return
        
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            lolbas_dir = data_dir / "lolbas"
            if lolbas_dir.exists():
                logger.info("Deleting existing LOLBAS directory: %s", lolbas_dir)
                shutil.rmtree(lolbas_dir)
            lolbas_dir.mkdir(exist_ok=True)
            logger.info("Extracting %s to %s", zip_file, lolbas_dir)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(lolbas_dir)
                yml_files = list(lolbas_dir.rglob("*.yml"))
                logger.info("Successfully extracted %s .yml files to %s", len(yml_files), lolbas_dir)
        except Exception as e:
            logger.error("Error processing LOLBAS zip file: %s", e)
    
    def process_artifacts_zip(self):
        zip_file = Path("artifacts-main.zip")
        if not zip_file.exists():
            logger.warning("Artifacts zip file %s does not exist, skipping.", zip_file)
            return
        
        temp_extract = None
        try:
            artifacts_dir = Path("data/artifacts").resolve()
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            temp_extract = Path("temp_artifacts_extract").resolve()
            if temp_extract.exists():
                remove_tree_safe(temp_extract, retry_delay=0.1)
                if temp_extract.exists():
                    logger.error("Failed to remove temp directory after retry")
                    return
            temp_extract.mkdir(parents=True, exist_ok=True)
            logger.info("Extracting %s to temporary location...", zip_file)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)
            
            source_yaml_dir = None
            primary_path = temp_extract / "artifacts-main" / "artifacts" / "data"
            if primary_path.exists():
                source_yaml_dir = primary_path
            else:
                alt_path = temp_extract / "artifacts" / "data"
                if alt_path.exists():
                    source_yaml_dir = alt_path
                else:
                    logger.warning("Expected directory %s does not exist. Searching case-insensitively...", primary_path)
                    found_dir = None
                    for root_dir in temp_extract.iterdir():
                        if root_dir.is_dir():
                            artifacts_dir_candidate = None
                            if root_dir.name.lower() == "artifacts-main":
                                artifacts_dir_candidate = root_dir / "artifacts" / "data"
                            elif root_dir.name.lower() == "artifacts":
                                artifacts_dir_candidate = root_dir / "data"
                            
                            if artifacts_dir_candidate and artifacts_dir_candidate.exists():
                                found_dir = artifacts_dir_candidate
                                break
                            for subdir in root_dir.rglob("artifacts/data"):
                                if subdir.is_dir():
                                    found_dir = subdir
                                    break
                            if found_dir:
                                break
                    
                    if found_dir:
                        source_yaml_dir = found_dir
                        logger.info("Found artifacts directory at: %s", found_dir)
                    else:
                        logger.error("Could not find artifacts/data directory in ZIP file.")
                        remove_tree_safe(temp_extract)
                        return
            if not source_yaml_dir or not source_yaml_dir.exists():
                logger.error("Could not locate artifacts/data directory in ZIP file.")
                remove_tree_safe(temp_extract)
                return
            yaml_files = []
            for pattern in ["*.yaml", "*.yml", "*.YAML", "*.YML"]:
                yaml_files.extend(source_yaml_dir.glob(pattern))
            yaml_files = list(set(yaml_files))
            if not yaml_files:
                logger.warning("No YAML files found in %s", source_yaml_dir)
                remove_tree_safe(temp_extract)
                return
            copied_count = 0
            for yaml_file in yaml_files:
                try:
                    dest_file = artifacts_dir / yaml_file.name
                    shutil.copy2(yaml_file, dest_file)
                    os.chmod(dest_file, 0o644)
                    copied_count += 1
                    logger.debug("Copied %s to %s", yaml_file.name, artifacts_dir)
                except PermissionError as e:
                    logger.error("Permission error copying %s: %s", yaml_file.name, e)
                    try:
                        os.chmod(yaml_file, 0o644)
                        shutil.copy2(yaml_file, dest_file)
                        os.chmod(dest_file, 0o644)
                        copied_count += 1
                    except Exception as e2:
                        logger.error("Failed to copy %s after permission fix: %s", yaml_file.name, e2)
                except Exception as e:
                    logger.error("Error copying %s: %s", yaml_file.name, e)
            logger.info("Successfully copied %s YAML files from %s found to %s", copied_count, len(yaml_files), artifacts_dir)
            remove_tree_safe(temp_extract)
            try:
                if "helper.artifacts" in sys.modules:
                    artifacts_module = sys.modules['helper.artifacts']
                    if hasattr(artifacts_module, 'ARTIFACTS_DATA_CACHE'):
                        artifacts_module.ARTIFACTS_DATA_CACHE = None
                        logger.info("Cleared artifacts data cache")
            except Exception as e:
                logger.warning("Could not clear artifacts cache: %s", e)
            
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file: %s", zip_file)
        except Exception as e:
            logger.error("Error processing artifacts zip file: %s", e)
            remove_tree_safe(temp_extract if temp_extract else None)
    def process_hijacklibs_zip(self):
        zip_file = Path("HijackLibs-main.zip")
        if not zip_file.exists():
            logger.warning("HijackLibs zip file %s does not exist, skipping.", zip_file)
            return
        temp_extract = None
        try:
            hijacklib_dir = Path("data/hijacklib").resolve()
            hijacklib_dir.mkdir(parents=True, exist_ok=True)
            temp_extract = Path("temp_hijacklibs_extract").resolve()
            if temp_extract.exists():
                remove_tree_safe(temp_extract, retry_delay=0.1)
                if temp_extract.exists():
                    logger.error("Failed to remove temp directory after retry")
                    return
            temp_extract.mkdir(parents=True, exist_ok=True)
            logger.info("Extracting %s to temporary location...", zip_file)
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(temp_extract)
            source_yml_dir = None
            primary_path = temp_extract / "HijackLibs-main" / "yml"
            if primary_path.exists():
                source_yml_dir = primary_path
            else:
                alt_path = temp_extract / "yml"
                if alt_path.exists():
                    source_yml_dir = alt_path
                else:
                    logger.warning("Expected directory %s does not exist. Searching case-insensitively...", primary_path)
                    found_dir = None
                    for root_dir in temp_extract.iterdir():
                        if root_dir.is_dir():
                            yml_dir_candidate = None
                            if root_dir.name.lower() == "hijacklibs-main":
                                yml_dir_candidate = root_dir / "yml"
                            elif root_dir.name.lower() == "yml":
                                yml_dir_candidate = root_dir
                            
                            if yml_dir_candidate and yml_dir_candidate.exists():
                                found_dir = yml_dir_candidate
                                break
                            for subdir in root_dir.rglob("yml"):
                                if subdir.is_dir():
                                    found_dir = subdir
                                    break
                            if found_dir:
                                break
                    
                    if found_dir:
                        source_yml_dir = found_dir
                        logger.info("Found yml directory at: %s", found_dir)
                    else:
                        logger.error("Could not find yml directory in ZIP file.")
                        remove_tree_safe(temp_extract)
                        return
            if not source_yml_dir or not source_yml_dir.exists():
                logger.error("Could not locate yml directory in ZIP file.")
                remove_tree_safe(temp_extract)
                return
            yml_files = []
            for pattern in ["*.yml", "*.yaml", "*.YML", "*.YAML"]:
                yml_files.extend(source_yml_dir.rglob(pattern))
            yml_files = list(set(yml_files))
            if not yml_files:
                logger.warning("No YML files found in %s", source_yml_dir)
                remove_tree_safe(temp_extract)
                return
            copied_count = 0
            for yml_file in yml_files:
                try:
                    rel_path = yml_file.relative_to(source_yml_dir)
                    dest_file = hijacklib_dir / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(yml_file, dest_file)
                    os.chmod(dest_file, 0o644)
                    copied_count += 1
                    logger.debug("Copied %s to %s", rel_path, hijacklib_dir)
                except PermissionError as e:
                    logger.error("Permission error copying %s: %s", yml_file.name, e)
                    try:
                        os.chmod(yml_file, 0o644)
                        rel_path = yml_file.relative_to(source_yml_dir)
                        dest_file = hijacklib_dir / rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(yml_file, dest_file)
                        os.chmod(dest_file, 0o644)
                        copied_count += 1
                    except Exception as e2:
                        logger.error("Failed to copy %s after permission fix: %s", yml_file.name, e2)
                except Exception as e:
                    logger.error("Error copying %s: %s", yml_file.name, e)
            logger.info("Successfully copied %s YML files from %s found to %s", copied_count, len(yml_files), hijacklib_dir)
            remove_tree_safe(temp_extract)
            try:
                if "helper.hijacklibs" in sys.modules:
                    hijacklibs_module = sys.modules['helper.hijacklibs']
                    if hasattr(hijacklibs_module, 'HIJACKLIBS_DATA_CACHE'):
                        hijacklibs_module.HIJACKLIBS_DATA_CACHE = None
                        logger.info("Cleared hijacklibs data cache")
            except Exception as e:
                logger.warning("Could not clear hijacklibs cache: %s", e)
            
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file: %s", zip_file)
        except Exception as e:
            logger.error("Error processing hijacklibs zip file: %s", e)
            remove_tree_safe(temp_extract if temp_extract else None)
    def process_sid_file(self):
        sid_file = Path("sid.yml")
        if not sid_file.exists():
            logger.warning("SID file %s does not exist, skipping.", sid_file)
            return
        try:
            microsoft_dir = Path("data/microsoft").resolve()
            microsoft_dir.mkdir(parents=True, exist_ok=True)
            dest_file = microsoft_dir / "sid.yml"
            try:
                shutil.copy2(sid_file, dest_file)
                os.chmod(dest_file, 0o644)
                logger.info("Successfully copied %s to %s", sid_file, dest_file)
            except PermissionError as e:
                logger.error("Permission error copying %s: %s", sid_file, e)
                try:
                    os.chmod(sid_file, 0o644)
                    shutil.copy2(sid_file, dest_file)
                    os.chmod(dest_file, 0o644)
                    logger.info("Successfully copied %s to %s after permission fix", sid_file, dest_file)
                except Exception as e2:
                    logger.error("Failed to copy %s after permission fix: %s", sid_file, e2)
            try:
                if "helper.resources.windows_sid" in sys.modules:
                    sid_module = sys.modules['helper.resources.windows_sid']
                    if hasattr(sid_module, 'SID_DATA_CACHE'):
                        sid_module.SID_DATA_CACHE = None
                        logger.info("Cleared SID data cache")
            except Exception as e:
                logger.warning("Could not clear SID cache: %s", e)
        except Exception as e:
            logger.error("Error processing SID file: %s", e)
    def process_lolesxi_zip(self):
        zip_file = Path("LOLESXi-main.zip")
        if not zip_file.exists():
            logger.warning("LOLESXi zip file %s does not exist, skipping.", zip_file)
            return
        temp_extract = None
        try:
            lolesxi_dir = Path("data/linux/lolesxi").resolve()
            lolesxi_dir.mkdir(parents=True, exist_ok=True)
            temp_extract = Path("temp_lolesxi_extract").resolve()
            if temp_extract.exists():
                remove_tree_safe(temp_extract, retry_delay=0.1)
                if temp_extract.exists():
                    logger.error("Failed to remove temp directory after retry")
                    return
            temp_extract.mkdir(parents=True, exist_ok=True)
            logger.info("Extracting %s to temporary location...", zip_file)
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(temp_extract)
            source_md_dir = None
            primary_path = temp_extract / "LOLESXi-main" / "_lolesxi" / "Binaries"
            if primary_path.exists():
                source_md_dir = primary_path
            else:
                alt_path = temp_extract / "_lolesxi" / "Binaries"
                if alt_path.exists():
                    source_md_dir = alt_path
                else:
                    logger.warning("Expected directory %s does not exist. Searching case-insensitively...", primary_path)
                    found_dir = None
                    for root_dir in temp_extract.iterdir():
                        if root_dir.is_dir():
                            lolesxi_dir_candidate = None
                            if root_dir.name.lower() == "lolesxi-main":
                                lolesxi_dir_candidate = root_dir / "_lolesxi" / "Binaries"
                            
                            if lolesxi_dir_candidate and lolesxi_dir_candidate.exists():
                                found_dir = lolesxi_dir_candidate
                                break
                            for subdir in root_dir.rglob("_lolesxi/Binaries"):
                                if subdir.is_dir():
                                    found_dir = subdir
                                    break
                            if found_dir:
                                break
                            for subdir in root_dir.rglob("*"):
                                if subdir.is_dir():
                                    path_str = str(subdir).lower()
                                    if "_lolesxi" in path_str and "binaries" in path_str:
                                        if subdir.parent.name.lower() == "_lolesxi" or any(
                                            p.name.lower() == "_lolesxi" for p in subdir.parents
                                        ):
                                            found_dir = subdir
                                            break
                            if found_dir:
                                break
                    if found_dir:
                        source_md_dir = found_dir
                        logger.info("Found Binaries directory at: %s", found_dir)
                    else:
                        logger.error("Could not find _lolesxi/Binaries directory in ZIP file.")
                        remove_tree_safe(temp_extract)
                        return
            if not source_md_dir or not source_md_dir.exists():
                logger.error("Could not locate _lolesxi/Binaries directory in ZIP file.")
                remove_tree_safe(temp_extract)
                return
            md_files = []
            for pattern in ["*.md", "*.MD", "*.Md", "*.mD"]:
                md_files.extend(source_md_dir.glob(pattern))
            md_files = list(set(md_files))
            if not md_files:
                logger.warning("No .md files found in %s", source_md_dir)
                remove_tree_safe(temp_extract)
                return
            copied_count = 0
            for md_file in md_files:
                try:
                    dest_file = lolesxi_dir / md_file.name
                    shutil.copy2(md_file, dest_file)
                    os.chmod(dest_file, 0o644)
                    copied_count += 1
                    logger.debug("Copied %s to %s", md_file.name, lolesxi_dir)
                except PermissionError as e:
                    logger.error("Permission error copying %s: %s", md_file.name, e)
                    try:
                        os.chmod(md_file, 0o644)
                        shutil.copy2(md_file, dest_file)
                        os.chmod(dest_file, 0o644)
                        copied_count += 1
                    except Exception as e2:
                        logger.error("Failed to copy %s after permission fix: %s", md_file.name, e2)
                except Exception as e:
                    logger.error("Error copying %s: %s", md_file.name, e)
            logger.info("Successfully copied %s .md files from %s found to %s", copied_count, len(md_files), lolesxi_dir)
            remove_tree_safe(temp_extract)
            try:
                if "helper.resources.lolesxi" in sys.modules:
                    lolesxi_module = sys.modules['helper.resources.lolesxi']
                    if hasattr(lolesxi_module, 'LOLESXI_DATA_CACHE'):
                        lolesxi_module.LOLESXI_DATA_CACHE = None
                        logger.info("Cleared LOLESXi data cache")
            except Exception as e:
                logger.warning("Could not clear LOLESXi cache: %s", e)
                
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file: %s", zip_file)
        except Exception as e:
            logger.error("Error processing LOLESXi zip file: %s", e)
            remove_tree_safe(temp_extract if temp_extract else None)
    def process_drivers_file(self):
        drivers_file = Path("drivers.json")
        if not drivers_file.exists():
            logger.warning("Drivers file %s does not exist, skipping.", drivers_file)
            return
        try:
            microsoft_dir = Path("data/microsoft").resolve()
            microsoft_dir.mkdir(parents=True, exist_ok=True)
            dest_file = microsoft_dir / "drivers.json"
            try:
                shutil.copy2(drivers_file, dest_file)
                os.chmod(dest_file, 0o644)
                logger.info("Successfully copied %s to %s", drivers_file, dest_file)
            except PermissionError as e:
                logger.error("Permission error copying %s: %s", drivers_file, e)
                try:
                    os.chmod(drivers_file, 0o644)
                    shutil.copy2(drivers_file, dest_file)
                    os.chmod(dest_file, 0o644)
                    logger.info("Successfully copied %s to %s after permission fix", drivers_file, dest_file)
                except Exception as e2:
                    logger.error("Failed to copy %s after permission fix: %s", drivers_file, e2)
            try:
                if "helper.resources.loldrivers" in sys.modules:
                    drivers_module = sys.modules['helper.resources.loldrivers']
                    if hasattr(drivers_module, 'LOLDRIVERS_DATA_CACHE'):
                        drivers_module.LOLDRIVERS_DATA_CACHE = None
                        logger.info("Cleared LOLDrivers data cache")
            except Exception as e:
                logger.warning("Could not clear LOLDrivers cache: %s", e)
        except Exception as e:
            logger.error("Error processing drivers file: %s", e)
    
    def cleanup_files(self, file_list):
        for file_to_delete in file_list:
            try:
                if os.path.exists(file_to_delete):
                    os.remove(file_to_delete)
                    logger.info("Deleted file: %s", file_to_delete)
            except OSError as e:
                logger.error("Error deleting file %s: %s", file_to_delete, e)
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
    urls = load_download_urls()
    if not urls:
        QMessageBox.warning(
            window,
            "No download sources",
            "No download links found. Ensure helper/download_links.yaml exists and contains filename -> URL entries.",
        )
        return
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    db_path = getattr(window, "db_path", "kanvas.db")
    dialog = DownloadProgressDialog(window)
    dialog.start_download(db_path, urls, headers)
    dialog.exec()