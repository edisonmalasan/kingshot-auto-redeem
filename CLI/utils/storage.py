"""
@Author: Edison Malasan
----------------
thread-safe JSON file storage.
all player data and code cache are persisted here.
uses atomic writes (write-to-temp then rename) to prevent corruption.
"""

import json
import os
import tempfile
import logging
from typing import Any

logger = logging.getLogger("kingshot")

# resolve paths relative to the project root (two levels up from this file)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve(filepath: str) -> str:
    """Convert a relative path to absolute using PROJECT_ROOT."""
    if not os.path.isabs(filepath):
        return os.path.join(PROJECT_ROOT, filepath)
    return filepath


def load_json(filepath: str, default: Any = None) -> Any:
    """
    Load JSON from a file.
    Returns `default` if the file doesn't exist or is corrupt.
    """
    filepath = _resolve(filepath)
    if not os.path.exists(filepath):
        logger.debug(f"File not found, using default: {filepath}")
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load {filepath}: {e}")
        return default if default is not None else {}


def save_json(filepath: str, data: Any) -> bool:
    """
    Atomically save data to a JSON file.
    Writes to a temp file first, then renames to prevent partial writes.

    Returns True on success, False on failure.
    """
    filepath = _resolve(filepath)
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)

    try:
        # write to a temp file in the same directory
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # atomic rename
        os.replace(tmp_path, filepath)
        logger.debug(f"Saved: {filepath}")
        return True
    except OSError as e:
        logger.error(f"Failed to save {filepath}: {e}")
        return False


def load_config(config_path: str = "json/config.json") -> dict:
    """Load the application configuration file."""
    config = load_json(config_path, default={})
    if not config:
        logger.warning("config.json not found or empty — using built-in defaults.")
    return config
