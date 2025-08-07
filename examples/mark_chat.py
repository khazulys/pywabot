# pylint: disable=duplicate-code
"""This is an example of how to mark a chat as read or unread."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")

@bot.on_message
async def handle_message(message):
    """Handles incoming messages and marks them as read or unread."""
    if "read this" in message.text.lower():
        await bot.mark_chat_as_read(message)

    elif "unread this" in message.text.lower():
        await bot.mark_chat_as_unread(message.chat)


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print("bot is ready for listen a message ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
