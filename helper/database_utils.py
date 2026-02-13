# Database utilities for Kanvas: create and manage SQLite tables (tor_list, bookmarks,
# system_types, entra_appid, cisa_ran_exploit, etc.) used throughout the application.
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
        "bookmarks",
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
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


def create_all_tables(db_path):
    for table_name, schema in TABLE_SCHEMAS:
        create_table(db_path, table_name, schema)
