import json
import os

SETTINGS_FILE = "app_settings.json"

DEFAULT_SETTINGS = {
    "boss_emails": ["7904001@gmail.com"],
    "auto_send_enabled": False,
    "auto_send_time": "17:00",
    "report_title_prefix": "Overnight"
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_SETTINGS, **settings}
    except:
        return DEFAULT_SETTINGS

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
