import os
import sys
import json
from pathlib import Path

# Base directory setup
def get_base_dir() -> Path:
    """Gets the base directory, considering whether the app is running as an executable or a script."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    # Running as script
    return Path(__file__).parent.resolve()

BASE_DIR = get_base_dir()
DB_PATH = BASE_DIR / "kovaaks_tracker.db"

# Application rules
PLAYS_PER_LEVEL = 100

SETTINGS_FILE = BASE_DIR / "settings.json"

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Failed to save settings: {e}")

def find_stats_folder() -> tuple[Path | None, str]:
    """
    Finds the KovaaK's stats folder automatically.
    Search order:
    1. Saved path in settings.json
    2. Parent directory's 'stats' folder
    3. Current directory's 'stats' folder
    
    Returns: (Path or None, Status String describing discovery method)
    """
    settings = load_settings()
    saved_path_str = settings.get("stats_folder")
    
    # 1. Saved Path
    if saved_path_str:
        saved_path = Path(saved_path_str)
        if saved_path.is_dir():
            return saved_path, "Saved"

    # 2. Auto-detect Parent
    candidate_1 = BASE_DIR.parent / "stats"
    if candidate_1.is_dir():
        return candidate_1, "Auto-detected"
    
    # 3. Auto-detect Current
    candidate_2 = BASE_DIR / "stats"
    if candidate_2.is_dir():
        return candidate_2, "Auto-detected"
        
    return None, "Not Found"
