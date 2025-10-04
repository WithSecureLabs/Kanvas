# code reviewed 
import sqlite3
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='kanvas.log')

def create_table(db_path, table_name, table_schema):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(table_schema)
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error creating table '{table_name}': {e}")
    finally:
        if conn:
            conn.close()


def create_all_tables(db_path):
    create_table(db_path, "user_settings", """
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            VT_API_KEY TEXT,
            SHODEN_API_KEY TEXT,
            OTX_API_KEY TEXT,
            openAI_API_KEY TEXT,
            MISP_API_KEY TEXT,
            OpenCTI_API_KEY TEXT,
            urlscan_API_KEY TEXT,
            vulners_API_KEY TEXT,
            malpedia_API_KEY TEXT,
            URLhaus_API_KEY TEXT,
            IPQS_API_KEY TEXT,
            HudonRock_API_KEY TEXT,
            ANTHROPIC_API_KEY TEXT,
            HIBP_API_KEY TEXT
        )
    """)


    create_table(db_path, "tor_list", """
        CREATE TABLE IF NOT EXISTS tor_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ipaddress_ TEXT UNIQUE,
            insert_date TEXT,
            source TEXT
        )
    """)

    create_table(db_path, "EvidenceType", """
        CREATE TABLE IF NOT EXISTS EvidenceType (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidencetype TEXT,
            sort_order TEXT,
            source TEXT
        )
    """)


    create_table(db_path, "ms_portals", """
        CREATE TABLE IF NOT EXISTS ms_portals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT,
            portal_name TEXT,
            source_file TEXT,
            primary_url TEXT
        )
    """)

    create_table(db_path, "bookmarks", """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT,
            portal_name TEXT,
            source_file TEXT,
            primary_url TEXT
        )
    """)

    create_table(db_path, "evtx_id", """
        CREATE TABLE IF NOT EXISTS evtx_id (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            description TEXT,
            category TEXT,
            Provider TEXT
        )
    """)

    create_table(db_path, "entra_appid", """
        CREATE TABLE IF NOT EXISTS entra_appid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            AppId TEXT,
            AppDisplayName TEXT,
            AppOwnerOrganizationId TEXT,
            Source TEXT,
            FileName TEXT
        )
    """)

    create_table(db_path, "mitre_techniques", """
        CREATE TABLE IF NOT EXISTS mitre_techniques (
            aid INTEGER PRIMARY KEY AUTOINCREMENT,
            PID TEXT,
            ID TEXT,
            Name TEXT
        )
    """)

    create_table(db_path, "mitre_tactics", """
        CREATE TABLE IF NOT EXISTS mitre_tactics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            url TEXT,
            created TEXT,
            modified TEXT
        )
    """)

    create_table(db_path, "system_types", """
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
    """)

    create_table(db_path, "icon_mappings", """
        CREATE TABLE IF NOT EXISTS icon_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_type_id INTEGER REFERENCES system_types(id),
            icon_filename TEXT NOT NULL,
            icon_type TEXT DEFAULT 'primary',
            color_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    create_table(db_path, "defend", """
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
    """)

    create_table(db_path, "cisa_ran_exploit", """
        CREATE TABLE IF NOT EXISTS cisa_ran_exploit (
            cveID TEXT,
            vendorProject TEXT,
            product TEXT,
            vulnerabilityName TEXT,
            knownRansomwareCampaignUse TEXT
        )
    """)