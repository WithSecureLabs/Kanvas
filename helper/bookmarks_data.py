# Bookmarks data for Kanvas: load/save bookmarks from two YAML files
# (bookmarks_downloaded.yaml, personal_bookmarks.yaml) and provide merged access.
# Reviewed 2026

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

PERSONAL_GROUP = "Personal"
EXCLUDED_GROUP = "Microsoft Portals via msportals.io"

_BASE_DIR = Path(__file__).resolve().parent
PATH_DOWNLOADED = _BASE_DIR / "bookmarks_downloaded.yaml"
PATH_PERSONAL = _BASE_DIR / "personal_bookmarks.yaml"


def _load_yaml(path):
    """Load a YAML file; return list (for bookmarks) or empty list on error."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            return []
        if not isinstance(data, list):
            logger.warning("Unexpected bookmarks format in %s: expected list", path)
            return []
        return data
    except (yaml.YAMLError, OSError) as e:
        logger.warning("Could not load %s: %s", path, e)
        return []


def _save_yaml(path, data):
    """Write data to YAML file (atomic: temp then replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        tmp.replace(path)
    except (yaml.YAMLError, OSError) as e:
        logger.error("Could not save %s: %s", path, e)
        raise
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def load_downloaded():
    """Return list of dicts: group_name, portal_name, source_file, primary_url."""
    raw = _load_yaml(PATH_DOWNLOADED)
    out = []
    for item in raw:
        if isinstance(item, dict):
            out.append({
                "group_name": item.get("group_name", ""),
                "portal_name": item.get("portal_name", ""),
                "source_file": item.get("source_file", ""),
                "primary_url": item.get("primary_url", ""),
            })
    return out


def load_personal():
    """Return list of dicts: portal_name, primary_url (group is always Personal)."""
    raw = _load_yaml(PATH_PERSONAL)
    out = []
    for item in raw:
        if isinstance(item, dict):
            out.append({
                "portal_name": item.get("portal_name", ""),
                "primary_url": item.get("primary_url", ""),
            })
    return out


def get_group_names():
    """Return sorted list of distinct group names, Personal first. Excludes EXCLUDED_GROUP."""
    downloaded = load_downloaded()
    groups = set()
    for row in downloaded:
        g = (row.get("group_name") or "").strip()
        if g and g != EXCLUDED_GROUP:
            groups.add(g)
    groups.add(PERSONAL_GROUP)
    others = sorted(g for g in groups if g != PERSONAL_GROUP)
    return [PERSONAL_GROUP] + others


def get_bookmarks_for_group(group_name):
    """Return list of (portal_name, primary_url) for the given group."""
    if group_name == PERSONAL_GROUP:
        rows = load_personal()
        return [(r["portal_name"], r["primary_url"]) for r in rows]
    downloaded = load_downloaded()
    out = []
    for row in downloaded:
        if (row.get("group_name") or "").strip() == group_name:
            out.append((row["portal_name"], row["primary_url"]))
    return out


def get_all_bookmarks_flat():
    """Return list of (group_name, portal_name, primary_url) for all bookmarks (for MS Portals / merged view)."""
    out = []
    for row in load_downloaded():
        g = (row.get("group_name") or "").strip()
        if g and g != EXCLUDED_GROUP:
            out.append((g, row["portal_name"], row["primary_url"]))
    for row in load_personal():
        out.append((PERSONAL_GROUP, row["portal_name"], row["primary_url"]))
    return out


def add_personal(portal_name, primary_url):
    """Add one Personal bookmark."""
    rows = load_personal()
    rows.append({"portal_name": portal_name.strip(), "primary_url": primary_url.strip()})
    _save_yaml(PATH_PERSONAL, rows)


def update_personal(old_name, new_name, new_url):
    """Update a Personal bookmark by old portal_name."""
    rows = load_personal()
    for r in rows:
        if (r.get("portal_name") or "").strip() == old_name:
            r["portal_name"] = new_name.strip()
            r["primary_url"] = new_url.strip()
            break
    _save_yaml(PATH_PERSONAL, rows)


def delete_personal(portal_name):
    """Remove one Personal bookmark by portal_name."""
    rows = load_personal()
    rows = [r for r in rows if (r.get("portal_name") or "").strip() != portal_name]
    _save_yaml(PATH_PERSONAL, rows)


def set_personal_bookmarks(rows):
    """
    Overwrite personal_bookmarks.yaml with list of dicts (portal_name, primary_url).
    Used for migration from DB; use add_personal/update_personal for normal edits.
    """
    data = [
        {"portal_name": (r.get("portal_name") or "").strip(), "primary_url": (r.get("primary_url") or "").strip()}
        for r in rows
    ]
    _save_yaml(PATH_PERSONAL, data)


def save_downloaded_bookmarks(rows):
    """
    Overwrite bookmarks_downloaded.yaml with list of dicts.
    Each dict: group_name, portal_name, source_file, primary_url.
    """
    data = []
    for r in rows:
        data.append({
            "group_name": r.get("group_name", ""),
            "portal_name": r.get("portal_name", ""),
            "source_file": r.get("source_file", ""),
            "primary_url": r.get("primary_url", ""),
        })
    _save_yaml(PATH_DOWNLOADED, data)
