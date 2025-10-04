import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import uuid
import re

logger = logging.getLogger(__name__)

def generate_stix_id(prefix: str = None) -> str:
    if prefix is None:
        prefix = "indicator"
    return f"{prefix}--{str(uuid.uuid4())}"

def escape_pattern_value(value: str) -> str:
    """Escape special characters in STIX pattern values"""
    return value.replace("\\", "\\\\").replace("'", "\\'")

def is_valid_ip(ip_str):
    import ipaddress
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def detect_indicator_type(value):
    if not value or pd.isna(value):
        return "Other-Strings"
    value = str(value).strip()
    if is_valid_ip(value):
        return "IPAddress"
    elif '.' in value and not value.startswith('http') and not value.startswith('ftp'):
        return "DomainName"
    elif value.startswith(('http://', 'https://', 'ftp://')):
        return "URL"
    elif len(value) == 64 and all(c in '0123456789abcdefABCDEF' for c in value):
        return "SHA256"
    elif len(value) == 40 and all(c in '0123456789abcdefABCDEF' for c in value):
        return "SHA1"
    elif len(value) == 32 and all(c in '0123456789abcdefABCDEF' for c in value):
        return "MD5"
    elif '@' in value and '.' in value:
        return "EmailAddress"
    else:
        return "Other-Strings"

def map_indicator_type_to_stix_pattern(indicator_type: str, value: str) -> str:
    if not value or pd.isna(value):
        return ""
    value = str(value).strip()
    escaped_value = escape_pattern_value(value)
    if indicator_type == "IPAddress":
        if ':' in value:
            return f"[ipv6-addr:value = '{escaped_value}']"
        else:
            return f"[ipv4-addr:value = '{escaped_value}']"
    elif indicator_type == "DomainName":
        return f"[domain-name:value = '{escaped_value}']"
    elif indicator_type == "URL":
        return f"[url:value = '{escaped_value}']"
    elif indicator_type == "FileName":
        return f"[file:name = '{escaped_value}']"
    elif indicator_type == "FilePath":
        return f"[file:path = '{escaped_value}']"
    elif indicator_type == "SHA256":
        return f"[file:hashes.'SHA-256' = '{escaped_value}']"
    elif indicator_type == "SHA1":
        return f"[file:hashes.'SHA-1' = '{escaped_value}']"
    elif indicator_type == "MD5":
        return f"[file:hashes.MD5 = '{escaped_value}']"
    elif indicator_type == "EmailAddress":
        return f"[email-addr:value = '{escaped_value}']"
    elif indicator_type == "UserName":
        return f"[user-account:account_login = '{escaped_value}']"
    elif indicator_type == "UserAgent":
        return f"[network-traffic:extensions.'http-request-ext'.request_header.'User-Agent' = '{escaped_value}']"
    elif indicator_type == "Mutex":
        return f"[mutex:name = '{escaped_value}']"
    elif indicator_type == "RegistryPath":
        return f"[windows-registry-key:key = '{escaped_value}']"
    elif indicator_type == "GPO":
        return f"[grouping:name = '{escaped_value}']"
    elif indicator_type == "JA3-JA3S":
        return f"[network-traffic:extensions.'tls-ext'.ja3_hash = '{escaped_value}']"
    elif indicator_type == "Other-Strings":
        return f"[artifact:payload_bin = '{escaped_value}']"
    else:
        return f"[artifact:payload_bin = '{escaped_value}']"

def map_indicator_type_to_stix_indicator_types(indicator_type: str) -> List[str]:
    mapping = {
        "IPAddress": ["malicious-activity"],
        "DomainName": ["malicious-activity"],
        "URL": ["malicious-activity"],
        "FileName": ["malicious-activity"],
        "FilePath": ["malicious-activity"],
        "EmailAddress": ["malicious-activity"],
        "UserName": ["malicious-activity"],
        "UserAgent": ["malicious-activity"],
        "Mutex": ["malicious-activity"],
        "RegistryPath": ["malicious-activity"],
        "GPO": ["malicious-activity"],
        "JA3-JA3S": ["malicious-activity"],
        "Other-Strings": ["malicious-activity"],
        "SHA256": ["malicious-activity"],
        "SHA1": ["malicious-activity"],
        "MD5": ["malicious-activity"]
    }
    return mapping.get(indicator_type, ["malicious-activity"])

def format_stix_timestamp(dt: datetime) -> str:
    formatted = dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    if len(formatted) > 23:  
        formatted = formatted[:23] + 'Z'
    return formatted

def convert_indicators_to_stix(excel_file_path: str, sheet_name: str = "Indicators") -> Dict[str, Any]:
    try:
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
        stix_bundle = {
            "type": "bundle",
            "id": f"bundle--{str(uuid.uuid4())}",
            "objects": []
        }
        processed_count = 0
        for index, row in df.iterrows():
            logger.info(f"Processing row {index}: {dict(row)}")
            indicator_type = ''
            indicator_value = ''
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower in ['indicatortype', 'indicator_type', 'type']:
                    indicator_type = str(row[col]) if pd.notna(row[col]) else ''
                elif col_lower in ['value', 'indicator', 'data', 'ioc', 'ip', 'domain', 'url']:
                    if pd.notna(row[col]) and str(row[col]).strip():
                        indicator_value = str(row[col]).strip()
            if not indicator_type and indicator_value:
                indicator_type = detect_indicator_type(indicator_value)
                logger.info(f"Auto-detected indicator type '{indicator_type}' for value '{indicator_value}'")
            if not indicator_type:
                indicator_type = 'Other-Strings'
            if not indicator_value:
                for col in df.columns:
                    if pd.notna(row[col]) and str(row[col]).strip():
                        indicator_value = str(row[col]).strip()
                        logger.info(f"Using value from column '{col}': {indicator_value}")
                        break
                if not indicator_value:
                    logger.warning(f"Skipping row {index}: no indicator value found in any column")
                    continue
            pattern = ""
            if 'SHA256' in row and pd.notna(row['SHA256']):
                sha256_value = str(row['SHA256']).strip()
                pattern = f"[file:hashes.'SHA-256' = '{sha256_value}'"
                if indicator_type == "FileName" and indicator_value:
                    pattern += f" AND file:name = '{indicator_value}'"
                pattern += "]"
            else:
                pattern = map_indicator_type_to_stix_pattern(indicator_type, indicator_value)
            if not pattern:
                logger.warning(f"Could not generate pattern for row {index}")
                continue
            stix_indicator_types = map_indicator_type_to_stix_indicator_types(indicator_type)
            current_time = datetime.utcnow()
            timestamp = format_stix_timestamp(current_time)
            indicator = {
                "type": "indicator",
                "spec_version": "2.1",
                "id": generate_stix_id("indicator"),
                "created": timestamp,
                "modified": timestamp,
                "name": str(row.get('name', f"{indicator_type} Indicator: {indicator_value}")),
                "description": str(row.get('description', f"{indicator_type} indicator: {indicator_value}")),
                "indicator_types": stix_indicator_types,
                "pattern": pattern,
                "pattern_type": "stix",
                "valid_from": timestamp
            }
            if 'confidence' in row and pd.notna(row['confidence']):
                try:
                    confidence = int(row['confidence'])
                    if 0 <= confidence <= 100:
                        indicator["confidence"] = confidence
                except (ValueError, TypeError):
                    pass
            if 'valid_until' in row and pd.notna(row['valid_until']):
                try:
                    if isinstance(row['valid_until'], str):
                        if 'T' in row['valid_until'] and row['valid_until'].endswith('Z'):
                            indicator["valid_until"] = row['valid_until']
                        else:
                            logger.warning(f"Invalid valid_until format: {row['valid_until']}")
                    else:
                        indicator["valid_until"] = format_stix_timestamp(row['valid_until'])
                except Exception as e:
                    logger.warning(f"Error processing valid_until: {e}")
            logger.info(f"Created indicator: {indicator['name']} with pattern: {pattern}")
            stix_bundle["objects"].append(indicator)
            processed_count += 1
        logger.info(f"Generated STIX bundle with {processed_count} indicators processed from {len(df)} rows")
        return stix_bundle
    except FileNotFoundError:
        logger.error(f"Excel file '{excel_file_path}' not found")
        raise FileNotFoundError(f"Excel file '{excel_file_path}' not found")
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        raise Exception(f"Error processing Excel file: {str(e)}")

