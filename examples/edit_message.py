"""
This is an example of how to edit a message."""
import asyncio
import logging
from pywabot import PyWaBot
from pywabot.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Store the ID of the message to be edited
MESSAGE_TO_EDIT = {}


async def main():
    """
    Initializes the bot, connects, and handles message editing.
    """

    bot = PyWaBot(session_name="my_bot_session", api_key="your api_key")

    @bot.handle_msg(".send")
    async def send_initial_message(message):
        """Sends a message and saves its details to be edited later."""
        global MESSAGE_TO_EDIT  # pylint: disable=global-statement
        logger.info("Received .send command. Sending initial message.")

        sent_message_data = await bot.send_message(
            message.chat, "This is the original message. Use .edit to change it."
        )
        if sent_message_data:
            MESSAGE_TO_EDIT = sent_message_data
            logger.info("Message sent. ID: %s", MESSAGE_TO_EDIT['key']['id'])
        else:
            logger.error("Failed to get message details after sending.")

    @bot.handle_msg(".edit")
    async def edit_sent_message(message):
        """Edits the previously sent message."""
        global MESSAGE_TO_EDIT  # pylint: disable=global-statement
        if not MESSAGE_TO_EDIT:
            await bot.send_message(message.chat, "You need to send a message with .send first.")
            return

        logger.info("Received .edit command. Editing message ID: %s", MESSAGE_TO_EDIT['key']['id'])
        new_text = "This message has been successfully edited!"

        await bot.edit_msg(
            recipient_jid=MESSAGE_TO_EDIT['key']['remoteJid'],
            message_id=MESSAGE_TO_EDIT['key']['id'],
            new_text=new_text
        )
        logger.info("Message edited successfully.")
        MESSAGE_TO_EDIT = {}  # Clear after editing

    # Connect the bot
    if await bot.connect():
        logger.info("Bot connected. Use .send and then .edit.")
        await bot.start_listening()
    else:
        logger.error("Failed to connect the bot.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
