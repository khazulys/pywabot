# pylint: disable=duplicate-code
"""This is an example of how to send a poll message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg('.poll')
async def handle_poll(message):
    """Sends a poll to the user."""
    poll_question = "What is your favorite color?"
    poll_options = ["Red", "Green", "Blue"]
    await bot.send_poll(message.chat, poll_question, poll_options)


async def main():
    """Connects the bot and starts listening for messages."""
    if not await bot.connect():
        return None

    print("bot is ready for incoming message...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
