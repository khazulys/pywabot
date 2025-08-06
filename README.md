# PyWaBot

[![PyPI version](https://img.shields.io/pypi/v/pywabot.svg)](https://pypi.org/project/pywabot/)
[![Python versions](https://img.shields.io/pypi/pyversions/pywabot.svg)](https://pypi.org/project/pywabot/)

**PyWaBot** is a powerful, asynchronous, and unofficial Python library for interacting with the WhatsApp Business Platform, using a Baileys-based API server. It provides a high-level, easy-to-use interface for sending messages, handling events, and managing your WhatsApp bot.

## Features

- **Asynchronous by Design**: Built with `asyncio` for high performance.
- **Easy to Use**: High-level, intuitive methods for common WhatsApp actions.
- **Rich Media Support**: Send and receive text, images, videos, documents, and more.
- **Session Management**: Programmatically list and delete WhatsApp sessions.
- **Secure**: Built-in API key authentication.
- **Event-Driven**: Use decorators to easily handle incoming messages.

## Requirements

- Python 3.8+

## Installation

You can install PyWaBot directly from PyPI:

```bash
pip install pywabot
```

## Getting Started

Follow these steps to get your bot up and running.

### 1. Generate an API Key

The library requires an API key to communicate with the server. A tool is included to generate a secure key.

From your project's root directory, create a file api_key_manager.py and copy-paste this code : 
```python
import secrets
import json
import os
import argparse

API_KEY_FILE = ".api_key.json"

def generate_api_key():
    """Generates and saves a new API key."""
    api_key = secrets.token_hex(24)
    with open(API_KEY_FILE, "w") as f:
        json.dump({"api_key": api_key}, f, indent=4)
    print(f"Generated new API key and saved to {API_KEY_FILE}")
    print(f"Your API Key: {api_key}")
    return api_key

def get_api_key():
    """Retrieves the saved API key."""
    if not os.path.exists(API_KEY_FILE):
        return None
    with open(API_KEY_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("api_key")
        except (json.JSONDecodeError, AttributeError):
            return None

def main():
    parser = argparse.ArgumentParser(
        description="A simple tool to generate and manage the API key for PyWaBot.",
        epilog="Example usage: python tools/api_key_manager.py generate"
    )
    
    subparsers = parser.add_subparsers(dest="action", required=True, help="Available actions")
    parser_generate = subparsers.add_parser("generate", help="Generate a new API key and save it.")
    
    parser_get = subparsers.add_parser("get", help="Get the currently saved API key.")

    args = parser.parse_args()

    if args.action == "generate":
        generate_api_key()
    elif args.action == "get":
        key = get_api_key()
        if key:
            print(f"API Key: {key}")
        else:
            print(f"API key not found in {API_KEY_FILE}. "
                  "Generate one using: python tools/api_key_manager.py generate")

if __name__ == "__main__":
    main()
```
and run :
```bash
python api_key_manager.py generate
```
This will create a `.api_key.json` file in your project root containing your unique key.

### 2. Write Your Bot

Here is a complete example of a simple echo bot.

`example_bot.py`:
```python
import asyncio
import json
import os
from pywabot import PyWaBot

API_KEY_FILE = ".api_key.json"

def get_api_key_from_file():
    if not os.path.exists(API_KEY_FILE):
        return None
    with open(API_KEY_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("api_key")
        except (json.JSONDecodeError, AttributeError):
            return None

async def manage_sessions(api_key):
    print("--- Session Management ---")
    
    print("\nListing available sessions...")
    try:
        sessions = await PyWaBot.list_sessions(api_key=api_key)
        if sessions:
            print("Found sessions:")
            for session in sessions:
                print(f"- {session}")
        else:
            print("No active sessions found.")
    except Exception as e:
        print(f"An error occurred while listing sessions: {e}")

async def main():
    print("Starting PyWaBot example...")

    api_key = get_api_key_from_file()
    if not api_key:
        print("\nERROR: API key not found!")
        print("Please generate one by running the following command from your terminal:")
        print("python tools/api_key_manager.py generate")
        return

    # You can run session management tasks before starting the bot.
    await manage_sessions(api_key)

    print("\n--- Bot Initialization ---")
    # Use a unique session_name for each WhatsApp account you want to run.
    session_name = "my_whatsapp_session"
    bot = PyWaBot(session_name=session_name, api_key=api_key)

    print(f"Connecting bot for session: '{session_name}'...")
    if not await bot.connect():
        print("\nFailed to connect. You may need to pair your device.")
        phone_number = input("Enter your WhatsApp phone number (e.g., 6281234567890) to get a pairing code: ")
        if phone_number:
            try:
                code = await bot.request_pairing_code(phone_number)
                if code:
                    print(f"\nPairing Code: {code}")
                    print("Enter this code on your phone (WhatsApp > Linked Devices > Link with phone number).")
                    print("Waiting for connection after pairing...")
                    if await bot.wait_for_connection(timeout=120):
                        print("Bot connected successfully!")
                    else:
                        print("Connection timed out after pairing.")
                        return
                else:
                    print("Could not request pairing code.")
                    return
            except Exception as e:
                print(f"An error occurred while requesting pairing code: {e}")
                return
        else:
            return

    print("Bot is connected and listening for messages...")

    @bot.on_message
    async def handle_all_messages(client: PyWaBot, message):
        if message.from_me:
            return
        
        print(f"\n[Message Received] From: {message.sender_name} | Chat: {message.chat}")
        print(f"-> Text: {message.text}")
        
        # Example: Reply to the message
        await client.typing(message.sender, duration=2)
        await client.send_message(
            recipient_jid=message.chat,
            text=f"Hi {message.sender_name}! You said: '{message.text}'"
        )
        print(f"Replied to {message.sender_name}")

    try:
        await bot.start_listening()
    except KeyboardInterrupt:
        print("\nStopping bot...")
    except Exception as e:
        print(f"\nAn error occurred while listening for messages: {e}")

if __name__ == "__main__":
    asyncio.run(main())

```

## Advanced Usage

### Sending Media

You can easily send different types of media.

```python
# Send an image with a caption
await bot.send_image(
    recipient_jid="1234567890@s.whatsapp.net",
    url="https://example.com/image.jpg",
    caption="Check out this cool image!"
)

# Send a video
await bot.send_video(
    recipient_jid="1234567890@s.whatsapp.net",
    url="https://example.com/video.mp4"
)

# Send an audio file
await bot.send_audio(
    recipient_jid="1234567890@s.whatsapp.net",
    url="https://example.com/audio.mp3"
)
```

### Session Management

You can list and delete sessions directly from your code. This is useful for maintenance and managing multiple accounts.

```python
import asyncio
from pywabot import PyWaBot

async def manage_sessions(api_key):
    print("--- Session Management ---")

    # List all sessions associated with the API key
    try:
        sessions = await PyWaBot.list_sessions(api_key=api_key)
        if sessions:
            print("Active sessions:", sessions)
        else:
            print("No active sessions found.")
    except Exception as e:
        print(f"Error listing sessions: {e}")

    # Delete a specific session
    session_to_delete = "old_session_name"
    print(f"\nAttempting to delete session: {session_to_delete}")
    try:
        success = await PyWaBot.delete_session(session_to_delete, api_key=api_key)
        if success:
            print(f"Session '{session_to_delete}' deleted successfully.")
        else:
            print(f"Failed to delete session '{session_to_delete}'.")
    except Exception as e:
        print(f"Error deleting session: {e}")

# Remember to replace "YOUR_API_KEY" with your actual key
# asyncio.run(manage_sessions(api_key="YOUR_API_KEY"))
```

## Troubleshooting

- **Pairing Code Timeout**: You have a limited time to enter the pairing code on your phone. If it expires, restart the bot to get a new code.

## Disclaimer

This is an unofficial library and is not affiliated with or endorsed by WhatsApp or Meta. Use it responsibly and in accordance with WhatsApp's terms of service.

## License

This project is licensed under the MIT License.
