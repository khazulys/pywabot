# pylint: disable=duplicate-code
"""This is an example of how to send a GIF message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg('.gif')
async def send_gif_command(message):
    """Sends a GIF to the user."""
    recipient_jid = message.chat
    gif_url = "https://media.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif"
    caption = "Here is your GIF!"

    await bot.typing(recipient_jid, duration=1)
    await bot.send_gif(recipient_jid, gif_url, caption)


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print('bot is ready for listening a message ...')
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
