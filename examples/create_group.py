# pylint: disable=duplicate-code
"""This is an example of how to create a group."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session", api_key="your api_key")

@bot.handle_msg('.create-group')
async def create_group(message):
    """Creates a new group with the specified participants."""
    recipient_jid = message.chat

    parts = message.text.split()
    if len(parts) < 3:
        await bot.typing(recipient_jid, duration=1)
        await bot.send_message(
            recipient_jid,
            "Usage: .create-group <GroupName> <participant1_jid> <participant2_jid> ..."
        )
        return

    group_title = parts[1]
    participants = [p for p in parts[2:] if '@' in p]

    if not participants:
        await bot.send_message(
            recipient_jid,
            "You must provide at least one valid participant JID (e.g., 1234567890@s.whatsapp.net)."
        )
        return

    try:
        group_info = await bot.create_group(group_title, participants)
        if group_info and group_info.get('id'):
            group_id = group_info.get('id')
            await bot.send_message(recipient_jid, f"Group '{group_title}' created successfully!")
            await bot.send_message(group_id, f"Welcome to the new group: {group_title}")
        else:
            await bot.send_message(recipient_jid, "Failed to create the group.")
    except Exception:  # pylint: disable=broad-except
        await bot.send_message(recipient_jid, "An error occurred while creating the group.")


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print('bot is ready for listening message ...')
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
