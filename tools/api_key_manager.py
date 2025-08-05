import secrets
import json
import os
import argparse

API_KEY_FILE = ".api_key.json"

def generate_api_key():
    """Generates and saves a new API key."""
    api_key = secrets.token_hex(24)
    with open(API_KEY_FILE, "w") as f:
        json.dump({"api_key": api_key}, f, indent=4)
    print(f"Generated new API key and saved to {API_KEY_FILE}")
    print(f"Your API Key: {api_key}")
    return api_key

def get_api_key():
    """Retrieves the saved API key."""
    if not os.path.exists(API_KEY_FILE):
        return None
    with open(API_KEY_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("api_key")
        except (json.JSONDecodeError, AttributeError):
            return None

def main():
    parser = argparse.ArgumentParser(
        description="A simple tool to generate and manage the API key for PyWaBot.",
        epilog="Example usage: python tools/api_key_manager.py generate"
    )
    
    subparsers = parser.add_subparsers(dest="action", required=True, help="Available actions")
    parser_generate = subparsers.add_parser("generate", help="Generate a new API key and save it.")
    
    parser_get = subparsers.add_parser("get", help="Get the currently saved API key.")

    args = parser.parse_args()

    if args.action == "generate":
        generate_api_key()
    elif args.action == "get":
        key = get_api_key()
        if key:
            print(f"API Key: {key}")
        else:
            print(f"API key not found in {API_KEY_FILE}. "
                  "Generate one using: python tools/api_key_manager.py generate")

if __name__ == "__main__":
    main()
