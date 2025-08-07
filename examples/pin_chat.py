# pylint: disable=duplicate-code
"""This is an example of how to pin and unpin a chat."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg('.pin')
async def pin_chat_command(message):
    """Pins the current chat."""
    recipient_jid = message.chat
    try:
        await bot.pin_chat(recipient_jid)
        await bot.send_message(recipient_jid, "Chat pinned!")
    except Exception:  # pylint: disable=broad-except
        await bot.send_message(recipient_jid, "Failed to pin chat.")


@bot.handle_msg('.unpin')
async def unpin_chat_command(message):
    """Unpins the current chat."""
    recipient_jid = message.chat
    try:
        await bot.unpin_chat(recipient_jid)
        await bot.send_message(recipient_jid, "Chat unpinned!")
    except Exception:  # pylint: disable=broad-except
        await bot.send_message(recipient_jid, "Failed to unpin chat.")


async def main():
    """Connects the bot and starts listening for messages."""
    if not await bot.connect():
        return None

    print("bot is ready for listen a message ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
