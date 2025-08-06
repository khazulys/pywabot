"""
Shared utility functions for the PyWaBot tools.

This module provides common functions, such as loading API keys or configuration,
to avoid code duplication across the different command-line tools.
"""
import json
from json import JSONDecodeError
import os

API_KEY_FILE = ".api_key.json"


def get_api_key():
    """
    Retrieves the saved API key from the .api_key.json file.

    This function looks for the API key file in the project's root directory.
    It handles potential errors like the file not existing or being malformed.

    Returns:
        str | None: The API key if found, otherwise None.
    """
    if not os.path.exists(API_KEY_FILE):
        return None
    try:
        with open(API_KEY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("api_key")
    except (JSONDecodeError, AttributeError, FileNotFoundError):
        return None
