# pylint: disable=duplicate-code
"""This is an example of how to handle incoming media messages."""
import asyncio
import os
from pywabot import PyWaBot

bot = PyWaBot(
    session_name="session_name", api_key="your api_key"
)


@bot.on_message
async def handle_media(message):
    """Handles incoming media messages and downloads them."""
    if message.location:
        location = message.get_location()
        await bot.send_message(
            message.chat,
            f"I see you are at {location['latitude']}, {location['longitude']}",
            reply_chat=message
        )

    elif message.document:
        filepath = await bot.download_media(message)
        if filepath:
            await bot.send_message(
                message.chat,
                f"I have saved the document as {os.path.basename(filepath)}"
            )

    elif message.image:
        filepath = await bot.download_media(message)
        if filepath:
            await bot.send_message(
                message.chat,
                f"I have saved the image as {os.path.basename(filepath)}"
            )

    elif message.video:
        filepath = await bot.download_media(message)
        if filepath:
            await bot.send_message(
                message.chat,
                f"I have saved the video as {os.path.basename(filepath)}"
            )

    elif message.audio:
        filepath = await bot.download_media(message)
        if filepath:
            await bot.send_message(
                message.chat,
                f"I have saved the audio as {os.path.basename(filepath)}"
            )

    else:
        await bot.send_message(
            message.chat, f"your message: {message.text}", reply_chat=message
        )


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print("bot is ready for listen a message ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
