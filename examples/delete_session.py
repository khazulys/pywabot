# pylint: disable=duplicate-code
"""This is an example of how to delete a session."""
import asyncio
import argparse
from pywabot import PyWaBot


async def main():
    """Deletes a session and verifies its removal."""
    parser = argparse.ArgumentParser(
        description="Delete a WhatsApp session from the PyWaBot server and verify its removal.",
        epilog="Example: python delete_session.py my_whatsapp_session"
    )
    parser.add_argument("session_name", help="The name of the session to delete.")
    args = parser.parse_args()

    session_to_delete = args.session_name
    api_key = "your api_key"

    if not api_key:
        print(f"Error: API key not found in {api_key}.")
        print("Please generate one first")
        return

    print(f"Attempting to delete session: '{session_to_delete}'...")

    try:
        success = await PyWaBot.delete_session(session_to_delete, api_key=api_key)
        if success:
            print(f"Server responded with success for deleting '{session_to_delete}'.")
        else:
            print(f"Server responded with failure for deleting '{session_to_delete}'.")
    except Exception as e:  # pylint: disable=broad-except
        print(f"An error occurred during the deletion request: {e}")
        return

    print("Verifying deletion...")
    await asyncio.sleep(1)

    try:
        sessions = await PyWaBot.list_sessions(api_key=api_key)
        print(f"Current sessions on server: {sessions or 'None'}")

        if session_to_delete not in sessions:
            print(
                f"Verification successful! Session '{session_to_delete}'"
                " is no longer on the server."
            )
        else:
            print(f"Verification FAILED! Session '{session_to_delete}' still exists on the server.")
            print("Please check the baileys-api-server logs for errors.")
    except Exception as e:  # pylint: disable=broad-except
        print(f"An error occurred during the verification request: {e}")


if __name__ == "__main__":
    asyncio.run(main())
