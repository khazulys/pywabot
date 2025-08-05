import asyncio
import json
import os
import argparse
from pywabot import PyWaBot

API_KEY_FILE = ".api_key.json"

def get_api_key_from_file():
    """Reads the API key from the JSON file."""
    if not os.path.exists(API_KEY_FILE):
        return None
    with open(API_KEY_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("api_key")
        except (json.JSONDecodeError, AttributeError):
            return None

async def main():
    """Main function to handle session deletion and verification."""
    parser = argparse.ArgumentParser(
        description="Delete a WhatsApp session from the PyWaBot server and verify its removal.",
        epilog="Example: python tools/delete_session.py my_whatsapp_session"
    )
    parser.add_argument("session_name", help="The name of the session to delete.")
    args = parser.parse_args()

    session_to_delete = args.session_name
    api_key = get_api_key_from_file()

    if not api_key:
        print(f"❌ Error: API key not found in {API_KEY_FILE}.")
        print("Please generate one first using: python tools/api_key_manager.py generate")
        return

    print(f"▶️ Attempting to delete session: '{session_to_delete}'...")

    # --- Deletion Step ---
    try:
        success = await PyWaBot.delete_session(session_to_delete, api_key=api_key)
        if success:
            print(f"✅ Server responded with success for deleting '{session_to_delete}'.")
        else:
            # This case might happen if the server returns success: false
            print(f"⚠️ Server responded with failure for deleting '{session_to_delete}'.")
            
    except Exception as e:
        print(f"❌ An error occurred during the deletion request: {e}")
        return

    # --- Verification Step ---
    print("\n🔎 Verifying deletion...")
    await asyncio.sleep(1)  # Give the server a moment just in case

    try:
        sessions = await PyWaBot.list_sessions(api_key=api_key)
        print(f"Current sessions on server: {sessions or 'None'}")

        if session_to_delete not in sessions:
            print(f"✔️ Verification successful! Session '{session_to_delete}' is no longer on the server.")
        else:
            print(f"❌ Verification FAILED! Session '{session_to_delete}' still exists on the server.")
            print("   Please check the baileys-api-server logs for errors.")

    except Exception as e:
        print(f"❌ An error occurred during the verification request: {e}")


if __name__ == "__main__":
    asyncio.run(main())
