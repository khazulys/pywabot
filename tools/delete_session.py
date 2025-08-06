"""
delete_session.py

This script provides a CLI tool to delete a WhatsApp session from the PyWaBot server.

It accepts a session name as an argument, attempts to delete it via the API,
and verifies whether the session was successfully removed.
"""

import argparse
import asyncio
from http import HTTPStatus

from shared import get_api_key
from pywabot import PyWaBot
from pywabot.exceptions import APIError


async def main():
    """
    Main function to handle session deletion and verification.

    Parses command-line arguments for the session name, retrieves the API key,
    and orchestrates the deletion and verification process.
    """
    parser = argparse.ArgumentParser(
        description="Delete a WhatsApp session from the PyWaBot server.",
        epilog="Example: python tools/delete_session.py my_whatsapp_session",
    )
    parser.add_argument(
        "session_name", help="The name of the session to delete."
    )
    args = parser.parse_args()

    session_to_delete = args.session_name
    api_key = get_api_key()

    if not api_key:
        print("❌ Error: API key not found.")
        print(
            "Please generate one first using: "
            "python tools/api_key_manager.py generate"
        )
        return

    print(f"▶️ Attempting to delete session: '{session_to_delete}'...")

    # --- Deletion Step ---
    try:
        success = await PyWaBot.delete_session(
            session_to_delete, api_key=api_key
        )
        if success:
            print(
                "✅ Server responded with success for deleting "
                f"'{session_to_delete}'."
            )
        else:
            print(
                "⚠️ Server responded with failure for deleting "
                f"'{session_to_delete}'."
            )

    except APIError as e:
        if e.status_code == HTTPStatus.NOT_FOUND:
            print(f"ℹ️ Session '{session_to_delete}' not found on the server.")
        else:
            print(
                "❌ An error occurred during the deletion request: "
                f"HTTP {e.status_code} - {e.message}"
            )
        return
    except (ConnectionError, OSError) as e:
        print(f"❌ A connection error occurred: {e}")
        return

    # --- Verification Step ---
    print("\n🔎 Verifying deletion...")
    await asyncio.sleep(1)  # Give the server a moment to process.

    try:
        sessions = await PyWaBot.list_sessions(api_key=api_key)
        print(f"Current sessions on server: {sessions or 'None'}")

        if session_to_delete not in sessions:
            print(
                "✔️ Verification successful! Session "
                f"'{session_to_delete}' is no longer on the server."
            )
        else:
            print(
                "❌ Verification FAILED! Session "
                f"'{session_to_delete}' still exists on the server."
            )
            print("   Please check the baileys-api-server logs for errors.")

    except (APIError, ConnectionError, OSError) as e:
        print(f"❌ An error occurred during the verification request: {e}")


if __name__ == "__main__":
    asyncio.run(main())
