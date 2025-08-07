# pylint: disable=duplicate-code
"""This is an example of how to send a message with a link preview."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg(".preview")
async def send_link_preview(message):
    """Sends a message with a link preview."""
    url_to_preview = "https://github.com/khazulys/pywabot"
    text_message = f"Check out this awesome library: {url_to_preview}"

    await bot.send_link_preview(message.chat, url_to_preview, text_message)


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print("bot is ready for listen a messsge ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
