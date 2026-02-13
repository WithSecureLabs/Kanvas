# Central constants for Kanvas Excel workbook structure: sheet names and column
# header names used by timeline, systems, indicators, accounts, and evidence
# tracker. Import these instead of hardcoding strings to keep references consistent.
#
# Excel Sheet Names
SHEET_TIMELINE = "Timeline"
SHEET_SYSTEMS = "Systems"

# Timeline Column Headers
COL_TIMESTAMP = "Timestamp_UTC_0"
COL_ACTIVITY = "Activity"
COL_MITRE_TACTIC = "MITRE Tactic"
COL_MITRE_TECHNIQUE = "MITRE Techniques"
COL_VISUALIZE = "Visualize"
COL_EVENT_SYSTEM = "Event System"
COL_REMOTE_SYSTEM = "Remote System"
COL_DIRECTION = "<->"

# Systems Column Headers
COL_HOSTNAME = "HostName"
COL_IP_ADDRESS = "IPAddress"
COL_SYSTEM_TYPE = "SystemType"

# Visualization Column Headers & Values
VAL_VISUALIZE_YES = "yes"

# Additional Sheet Names
SHEET_INDICATORS = "Indicators"
SHEET_ACCOUNTS = "Accounts"
SHEET_EVIDENCE_TRACKER = "Evidence Tracker"
SHEET_VERIS = "VERIS"

# Additional Column Headers
COL_SUSPECT_ACCOUNT = "Suspect Account"
COL_NOTES = "Notes"
COL_NOTE = "Note"
COL_DATE_ADDED = "Date Added"
COL_DATE_UPDATED = "Date Updated"
COL_DATE_COMPLETED = "Date Completed"
COL_DATE_REQUESTED = "Date Requested"
COL_DATE_RECEIVED = "Date Received"
COL_INDICATOR_TYPE = "IndicatorType"
COL_LOCATION = "Location"
COL_CURRENT_STATUS = "CurrentStatus"
COL_PRIORITY = "Priority"
COL_EVIDENCE_COLLECTED = "EvidenceCollected"
COL_TARGET_TYPE = "TargetType"
COL_ACCOUNT_TYPE = "AccountType"
COL_ENTRY_POINT = "EntryPoint"
COL_TLP = "TLP"
COL_EVIDENCE_TYPE = "EvidenceType"
