# pylint: disable=duplicate-code
"""This is an example of how to forward a message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")

FORWARD_TARGET_JID = '628978397772@s.whatsapp.net'


@bot.handle_msg('.forward')
async def handle_forward(message):
    """Forwards the message to the specified JID."""
    if await bot.forward_msg(FORWARD_TARGET_JID, message):
        await bot.send_message(
            message.sender, "Your message has been forwarded.", reply_chat=message
        )
    else:
        return False


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print("bot is ready for listening a message ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
