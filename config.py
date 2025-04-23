from os.path import expanduser
from pathlib import Path
import json
import os

# Default configuration
DEFAULT_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
    "segments_amount": 64,
    "download_path": str(Path(expanduser("~")) / "downloads"),
    "retry_times": 32,
    "chunk_size": 8192,  # 8KB chunks for better memory efficiency
    "timeout": 3600,
    "progress_bar": True,
}

# Create config directory if it doesn't exist
CONFIG_DIR = Path(expanduser("~")) / ".pydownloader"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config():
    """Load configuration from file or create with defaults"""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Update with any missing defaults
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
        return config
    except Exception as e:
        print(f"Error loading config: {e}. Using defaults.")
        return DEFAULT_CONFIG

# Load configuration
config = load_config()

# Extract common configuration variables for backward compatibility
user_agent = config["user_agent"]
segments_amount = config["segments_amount"]
store_pth = config["download_path"]
trytimes_when_failed = config["retry_times"]

# Ensure download directory exists
os.makedirs(store_pth, exist_ok=True)
