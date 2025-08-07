# pylint: disable=duplicate-code
"""This is an example of how to send an image message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg('.image')
async def send_image_command(message):
    """Sends an image to the user."""
    recipient_jid = message.chat

    image_url = (
        "https://p.kindpng.com/picc/s/134-1345330_python-logo-png-transparent-background"
        "-python-logo-png.png"
    )
    caption = "This is a Python logo!"

    await bot.typing(recipient_jid, duration=1)
    await bot.send_image(recipient_jid, image_url, caption)


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print("bot is ready for listening a message")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
