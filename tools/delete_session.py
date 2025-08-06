"""
A command-line tool to delete a WhatsApp session from the PyWaBot server.

This script connects to the server using a configured API key, issues a
deletion command for a specified session, and then verifies that the session
has been removed by listing the current sessions.
"""
import argparse
import asyncio
from http import HTTPStatus

from pywabot import PyWaBot
from pywabot.exceptions import PyWaBotAPIError

from shared import get_api_key


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
                f