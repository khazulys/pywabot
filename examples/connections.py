# pylint: disable=duplicate-code
"""This is an example of how to manage sessions."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


async def manage_sessions(apikey):
    """Lists all active sessions."""
    try:
        sessions = await PyWaBot.list_sessions(api_key=apikey)
        if sessions:
            print("found session!")
            for session in sessions:
                print(f"- {session}")

        else:
            print("no active session found!")
    except Exception as err:  # pylint: disable=broad-except
        print(f"An error occurred while listing sessions: {err}")


async def main():
    """Manages sessions and connects the bot."""
    await manage_sessions("your api_key")

    if not await bot.connect():
        phone_number = int(input("enter ur phone number (e.g, 628): "))
        if phone_number:
            try:
                code = await bot.request_pairing_code(phone_number)
                if code:
                    print(f"your pairing code: {code}")
                    print("waiting connection after pairing")
                    if await bot.wait_for_connection(timeout=120):
                        print("Bot connected successfully!")
                    else:
                        print("connection timeout after pairing")

                else:
                    print("failed to request pairing code")
            except Exception as err:  # pylint: disable=broad-except
                print(f"An error occurred while requesting pairing code: {err}")

        else:
            return False

    print("bot is connected and listening for message ...")

    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
