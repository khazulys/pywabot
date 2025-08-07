# pylint: disable=duplicate-code
"""This is an example of how to manage group participants."""
import asyncio
from pywabot import PyWaBot

bot = PyWaBot(session_name="session_name", api_key="your api_key")


async def manage_participants(message, action):
    """Manages group participants based on the given action."""
    if not message.chat.endswith('@g.us'):
        await bot.send_message(
            message.chat, "This command can only be used in a group."
        )
        return

    parts = message.text.split()
    if len(parts) < 2:
        await bot.send_message(
            message.chat,
            f"Usage: .{action} <participant1_jid> <participant2_jid> ..."
        )
        return

    participants = [p.replace('@', '') + '@s.whatsapp.net' for p in parts[1:]]

    try:
        await bot.update_group_participants(message.chat, action, participants)
        await bot.send_message(
            message.chat, f"Successfully performed action: {action}"
        )
    except Exception:  # pylint: disable=broad-except
        await bot.send_message(message.chat, f"Failed to perform action: {action}")


@bot.handle_msg('.add')
async def add_command(message):
    """Adds participants to the group."""
    await manage_participants(message, 'add')


@bot.handle_msg('.remove')
async def remove_command(message):
    """Removes participants from the group."""
    await manage_participants(message, 'remove')


@bot.handle_msg('.promote')
async def promote_command(message):
    """Promotes participants to admin."""
    await manage_participants(message, 'promote')


@bot.handle_msg('.demote')
async def demote_command(message):
    """Demotes participants from admin."""
    await manage_participants(message, 'demote')


async def main():
    """Connects the bot and starts listening."""
    if not await bot.connect():
        return None

    print('bot is ready for listening a message ...')
    await bot.start_listening()


if __name__ == "__main__":
    asyncio.run(main())
