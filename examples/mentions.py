# pylint: disable=duplicate-code
"""This is an example of how to send mentions."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


@bot.handle_msg('.mention')
async def handle_mention(message):
    """Handles the .mention command to demonstrate mentioning users."""
    sender_id = message.sender

    if message.chat.endswith('@g.us'):
        await bot.send_message_mention_all(
            message.chat, "Attention all group members!"
        )

    else:
        text_reply = f"Hi @{sender_id.split('@')[0]}, this is a mention for you."
        await bot.typing(sender_id, duration=1)
        await bot.send_mention(
            sender_id, text_reply, reply_chat=message, mentions=[sender_id]
        )


async def main():
    """Connects the bot and starts listening for messages."""
    if not await bot.connect():
        return None

    print("bot is ready for listen a message ...")
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
