"""
A command-line tool to generate and manage the API key for PyWaBot.

This script provides actions to securely generate a new API key or
retrieve the currently configured one. The key is stored in a local
'.api_key.json' file in the project root.
"""
import argparse
import json
import secrets

from shared import API_KEY_FILE, get_api_key


def generate_and_save_api_key():
    """
    Generates a new API key and saves it to the designated file.

    A cryptographically secure key is generated and stored in JSON format.
    This will overwrite any existing key file.

    Returns:
        str: The newly generated API key.
    """
    api_key = secrets.token_hex(24)
    try:
        with open(API_KEY_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": api_key}, f, indent=4)
        print(f"Generated new API key and saved to '{API_KEY_FILE}'")
        print(f"Your API Key: {api_key}")
        return api_key
    except IOError as e:
        print(f"Error: Could not write to file '{API_KEY_FILE}': {e}")
        return None


def main():
    """
    Main function to parse arguments and execute the requested action.
    """
    parser = argparse.ArgumentParser(
        description="A simple tool to generate and manage the API key for PyWaBot.",
        epilog="Example: python tools/api_key_manager.py generate",
    )

    subparsers = parser.add_subparsers(
        dest="action", required=True, help="Available actions"
    )

    # Sub-parser for the "generate" action
    _ = subparsers.add_parser(
        "generate", help="Generate a new API key and save it."
    )

    # Sub-parser for the "get" action
    _ = subparsers.add_parser("get", help="Get the currently saved API key.")

    args = parser.parse_args()

    if args.action == "generate":
        generate_and_save_api_key()
    elif args.action == "get":
        key = get_api_key()
        if key:
            print(f"API Key: {key}")
        else:
            print(
                f"API key not found in '{API_KEY_FILE}'. "
                "Generate one using: python tools/api_key_manager.py generate"
            )


if __name__ == "__main__":
    main()