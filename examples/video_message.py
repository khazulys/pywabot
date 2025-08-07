# pylint: disable=duplicate-code
"""This is an example of how to send a video message."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg('.video')
async def send_video_command(message):
    """Sends a video to the user."""
    recipient_jid = message.chat

    video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
    caption = "Big Buck Bunny!"

    await bot.typing(recipient_jid, duration=1)
    await bot.send_message(
        message.chat,
        f"Tunggu sebentar ya {message.sender_name}, video kamu lagi aku proses",
        reply_chat=message
    )
    await bot.send_video(recipient_jid, video_url, caption)


async def main():
    """Connects the bot and starts listening for messages."""
    if not await bot.connect():
        return None

    print("bot is ready for incoming message ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
