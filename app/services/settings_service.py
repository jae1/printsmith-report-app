import json
import os

SETTINGS_FILE = "app_settings.json"

DEFAULT_SETTINGS = {
    "boss_emails": ["7904001@gmail.com"],
    "auto_send_enabled": False,
    "auto_send_time": "17:00",
    "auto_send_days": [0, 1, 2, 3, 4], # Mon-Fri
    "auto_sync_receipts": False,
    "report_title_prefix": "Overnight",
    "excluded_paid_accounts": [
        "Belltown Minuteman Press",
        "Federal Way Minuteman Press",
        "Green River Printing"
    ]
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = {**DEFAULT_SETTINGS, **settings}
            
            # Force add subsidiary accounts
            subsidiaries = [
                "Belltown Minuteman Press",
                "Federal Way Minuteman Press",
                "Green River Printing"
            ]
            excluded = set(merged.get("excluded_paid_accounts", []))
            excluded.update(subsidiaries)
            merged["excluded_paid_accounts"] = list(excluded)
            
            return merged
    except:
        return DEFAULT_SETTINGS

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
