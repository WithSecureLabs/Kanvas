# Database utilities for Kanvas: create and manage SQLite tables (tor_list,
# ms_portals, system_types, entra_appid, cisa_ran_exploit, etc.) used throughout
# the application. Bookmarks are stored in YAML (helper/bookmarks_data.py).
# Reviewed on 01/02/2026 by Jinto Antony

import logging
import sqlite3

logger = logging.getLogger(__name__)

TABLE_SCHEMAS = [
    (
        "tor_list",
        """
        CREATE TABLE IF NOT EXISTS tor_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ipaddress_ TEXT UNIQUE,
            insert_date TEXT,
            source TEXT
        )
        """,
    ),
    (
        "EvidenceType",
        """
        CREATE TABLE IF NOT EXISTS EvidenceType (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidencetype TEXT,
            sort_order TEXT,
            source TEXT
        )
        """,
    ),
    (
        "ms_portals",
        """
        CREATE TABLE IF NOT EXISTS ms_portals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT,
            portal_name TEXT,
            source_file TEXT,
            primary_url TEXT
        )
        """,
    ),
    (
        "evtx_id",
        """
        CREATE TABLE IF NOT EXISTS evtx_id (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            description TEXT,
            category TEXT,
            Provider TEXT
        )
        """,
    ),
    (
        "entra_appid",
        """
        CREATE TABLE IF NOT EXISTS entra_appid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            AppId TEXT,
            AppDisplayName TEXT,
            AppOwnerOrganizationId TEXT,
            Source TEXT,
            FileName TEXT
        )
        """,
    ),
    (
        "mitre_techniques",
        """
        CREATE TABLE IF NOT EXISTS mitre_techniques (
            aid INTEGER PRIMARY KEY AUTOINCREMENT,
            PID TEXT,
            ID TEXT,
            Name TEXT
        )
        """,
    ),
    (
        "mitre_tactics",
        """
        CREATE TABLE IF NOT EXISTS mitre_tactics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            url TEXT,
            created TEXT,
            modified TEXT
        )
        """,
    ),
    (
        "system_types",
        """
        CREATE TABLE IF NOT EXISTS system_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            category TEXT NOT NULL,
            icon_filename TEXT,
            fallback_color TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ),
    (
        "icon_mappings",
        """
        CREATE TABLE IF NOT EXISTS icon_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_type_id INTEGER REFERENCES system_types(id),
            icon_filename TEXT NOT NULL,
            icon_type TEXT DEFAULT 'primary',
            color_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ),
    (
        "defend",
        """
        CREATE TABLE IF NOT EXISTS defend (
            query_def_tech_label TEXT,
            top_def_tech_label TEXT,
            def_tactic_label TEXT,
            def_tactic_rel_label TEXT,
            def_tech_label TEXT,
            def_artifact_rel_label TEXT,
            def_artifact_label TEXT,
            off_artifact_label TEXT,
            off_artifact_rel_label TEXT,
            off_tech_label TEXT,
            off_tech_id TEXT,
            off_tech_parent_label TEXT,
            off_tech_parent_is_toplevel TEXT,
            off_tactic_rel_label TEXT,
            off_tactic_label TEXT,
            def_tactic TEXT,
            def_tactic_rel TEXT,
            def_tech TEXT,
            def_artifact_rel TEXT,
            def_artifact TEXT,
            off_artifact TEXT,
            off_artifact_rel TEXT,
            off_tech TEXT,
            off_tech_parent TEXT,
            off_tactic_rel TEXT,
            off_tactic TEXT
        )
        """,
    ),
    (
        "cisa_ran_exploit",
        """
        CREATE TABLE IF NOT EXISTS cisa_ran_exploit (
            cveID TEXT,
            vendorProject TEXT,
            product TEXT,
            vulnerabilityName TEXT,
            knownRansomwareCampaignUse TEXT
        )
        """,
    ),
]


def create_table(db_path, table_name, table_schema):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(table_schema)
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error creating table '%s': %s", table_name, e)
    finally:
        if conn:
            conn.close()


def _migrate_bookmarks_to_yaml_and_drop(db_path):
    """If bookmarks table exists, migrate ALL rows to YAML (downloaded + Personal) then drop table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bookmarks'"
        )
        if not cursor.fetchone():
            conn.close()
            return
        cursor.execute(
            "SELECT group_name, portal_name, source_file, primary_url FROM bookmarks"
        )
        all_rows = cursor.fetchall()
        conn.close()

        from helper import bookmarks_data

        personal = [
            {"portal_name": r[1], "primary_url": r[3]}
            for r in all_rows
            if (r[0] or "").strip() == "Personal"
        ]
        downloaded = [
            {
                "group_name": r[0] or "",
                "portal_name": r[1] or "",
                "source_file": r[2] or "",
                "primary_url": r[3] or "",
            }
            for r in all_rows
            if (r[0] or "").strip() != "Personal"
        ]
        if downloaded and not bookmarks_data.load_downloaded():
            bookmarks_data.save_downloaded_bookmarks(downloaded)
            logger.info(
                "Migrated %d downloaded bookmarks from DB to YAML",
                len(downloaded),
            )
        if personal and not bookmarks_data.load_personal():
            bookmarks_data.set_personal_bookmarks(personal)
            logger.info(
                "Migrated %d Personal bookmarks from DB to YAML",
                len(personal),
            )
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS bookmarks")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='bookmarks'")
        conn.commit()
        conn.close()
        logger.info("Dropped bookmarks table (bookmarks now use YAML)")
    except Exception as e:
        logger.warning("Could not migrate/drop bookmarks table: %s", e)


def create_all_tables(db_path):
    for table_name, schema in TABLE_SCHEMAS:
        create_table(db_path, table_name, schema)
    _migrate_bookmarks_to_yaml_and_drop(db_path)
