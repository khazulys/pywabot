# pylint: disable=duplicate-code
"""This is an example of how to react to a message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.on_message
async def react_to_message(message):
    """Reacts to every incoming message with a thumbs up."""
    await bot.send_reaction(message, "👍")


async def main():
    """Connects the bot and starts listening for messages."""
    if not await bot.connect():
        return None

    print("bot is ready for incoming message...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
