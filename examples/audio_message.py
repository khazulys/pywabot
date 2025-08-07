# pylint: disable=duplicate-code
"""This is an example of sending an audio message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg(".audio")
async def send_audio_command(message):
    """Sends an audio file to the user."""
    print(f"Received .audio command from {message.sender_name}")

    audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

    await bot.typing(message.sender, duration=2)
    await bot.send_message(message.chat, "Sending an audio message ...")
    await bot.send_audio(message.chat, url=audio_url)


async def main():
    """Connects the bot and starts listening."""
    if await bot.connect():
        print("Bot is ready!")
        await bot.start_listening()
    else:
        return False


if __name__ == "__main__":
    asyncio.run(main())
