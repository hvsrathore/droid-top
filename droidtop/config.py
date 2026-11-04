"""
DroidTop - Persistent Configuration and User Preferences.
Stored in ~/.config/droidtop/config.json.
"""

import os
import json
from typing import Dict, Any


DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "btop",
    "refresh_rate": 1.0,
    "default_view": "overview",
    "enable_mouse": True,
    "sort_by": "CPU%",
    "sort_desc": True,
}


class Config:
    """Manages reading and writing application settings."""

    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/droidtop")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        self.data.update(saved)
            except Exception:
                pass

    def save(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save()
