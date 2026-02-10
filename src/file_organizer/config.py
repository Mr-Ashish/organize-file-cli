"""Configuration for file organizer."""

# Mapping of categories to file extensions
# This can be extended or loaded from file in future
FILE_TYPE_MAPPINGS = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".ppt", ".pptx"},
    "videos": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".aac"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "code": {".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs"},
    "other": set(),  # catch-all
}

# Ignored files/directories
IGNORED = {".", "..", ".git", "__pycache__", "node_modules"}

# Size categories (in bytes; extensible)
SIZE_THRESHOLDS = {
    "small": 1 * 1024 * 1024,      # < 1MB
    "medium": 100 * 1024 * 1024,   # 1MB - 100MB
    # large: >100MB
}

# Support for folders as category in type mode
FOLDERS_CATEGORY = "folders"

# Known category names to skip re-moving (avoids self-nesting on re-run)
KNOWN_CATEGORIES = set(FILE_TYPE_MAPPINGS.keys()) | {"small", "medium", "large", FOLDERS_CATEGORY}
# Note: date modes (YYYY-MM) skipped dynamically in collection

import json
from pathlib import Path

# Load runtime config (overrides defaults; user-editable)
CONFIG_PATH = Path(__file__).parent / "config.json"
try:
    with open(CONFIG_PATH) as f:
        RUNTIME_CONFIG = json.load(f)
except Exception:
    RUNTIME_CONFIG = {}

# Override with runtime config
size_cfg = RUNTIME_CONFIG.get("size", {})
SIZE_THRESHOLDS = size_cfg.get("thresholds", SIZE_THRESHOLDS)
DATE_FORMAT = RUNTIME_CONFIG.get("date", {}).get("format", "%Y-%m")
UI_CFG = RUNTIME_CONFIG.get("ui", {})
INTERACTIVE_CFG = RUNTIME_CONFIG.get("interactive", {})

# Update mappings from runtime extensions
for cat, exts in RUNTIME_CONFIG.get("extensions", {}).items():
    if cat in FILE_TYPE_MAPPINGS:
        FILE_TYPE_MAPPINGS[cat] = set(exts)
    else:
        FILE_TYPE_MAPPINGS[cat] = set(exts)
KNOWN_CATEGORIES = set(FILE_TYPE_MAPPINGS.keys()) | {"small", "medium", "large", FOLDERS_CATEGORY}
