# PyWaBot

[![PyPI version](https://img.shields.io/pypi/v/pywabot.svg)](https://pypi.org/project/pywabot/)

**PyWaBot** is a powerful, asynchronous, and unofficial Python library for interacting with the WhatsApp Business Platform. Built on a Baileys-based API server, it provides a high-level, easy-to-use interface for sending messages, handling events, and managing your WhatsApp bot.

## Features

- **Asynchronous by Design**: Built with `asyncio` for high performance and non-blocking operations.
- **Easy to Use**: A high-level, intuitive API for common WhatsApp actions.
- **Pairing Code Login**: Easily connect your bot by requesting a pairing code—no need to scan a QR code.
- **Rich Media Support**: Send and receive text, images, videos, documents, and more.
- **Session Management**: Programmatically list and delete active WhatsApp sessions.
- **Event-Driven**: Use simple decorators to handle incoming messages and commands.

## Installation

You can install PyWaBot directly from PyPI:

```bash
pip install pywabot
```

## Getting Started: Your First Connection

Follow these steps to get your bot connected and running in minutes.

### 1. Get Your API Key

The library communicates with a secure API server that requires an API key. A utility script is included to generate one for you.

First, create a file named `api_key_manager.py` in your project's root directory and add the following code:

```python
# tools/api_key_manager.py
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
        epilog="Example usage: python api_key_manager.py generate"
    )
    subparsers = parser.add_subparsers(dest="action", required=True, help="Available actions")
    subparsers.add_parser("generate", help="Generate a new API key and save it.")
    subparsers.add_parser("get", help="Get the currently saved API key.")
    args = parser.parse_args()

    if args.action == "generate":
        generate_api_key()
    elif args.action == "get":
        key = get_api_key()
        if key:
            print(f"API Key: {key}")
        else:
            print(f"API key not found. Generate one using: python api_key_manager.py generate")

if __name__ == "__main__":
    main()
```

Now, run the script from your terminal to generate the key:

```bash
python api_key_manager.py generate
```

This will create a `.api_key.json` file in your project root. Keep this file secure and do not share it.

### 2. Connect Your Bot with a Pairing Code

Create a file named `my_bot.py` and use the following code to connect your bot. This example shows how to request a pairing code if the bot is not already connected.

```python
# my_bot.py
import asyncio
from pywabot import PyWaBot

# --- Configuration ---
# Give your session a unique name to distinguish it from other bots
SESSION_NAME = "my_first_bot" 
# Replace with the API key you generated
API_KEY = "your_api_key"

async def main():
    """Initializes the bot and connects using a pairing code if needed."""
    bot = PyWaBot(session_name=SESSION_NAME, api_key=API_KEY)

    print("Attempting to connect the bot...")
    if not await bot.connect():
        print("\nConnection failed. A pairing code is required.")
        
        try:
            phone_number = input("Enter your WhatsApp phone number (e.g., 6281234567890): ")
            if phone_number:
                code = await bot.request_pairing_code(phone_number)
                if code:
                    print(f"\n>>> Your Pairing Code: {code} <<<")
                    print("Go to WhatsApp on your phone > Linked Devices > Link with phone number.")
                    print("Enter the code to connect your bot.")
                    
                    print("\nWaiting for connection...")
                    if await bot.wait_for_connection(timeout=120):
                        print("Bot connected successfully!")
                    else:
                        print("Connection timed out. Please try running the script again.")
                else:
                    print("Could not request a pairing code. Please check your API key and server status.")
        except Exception as e:
            print(f"An error occurred: {e}")
            return

    print("Bot is connected and ready to listen for messages!")
    # The bot will keep running until you stop it (e.g., with Ctrl+C)
    await bot.start_listening()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
```

**To run your bot:**
1.  Replace `"your_api_key"` with the key from your `.api_key.json` file.
2.  Run the script: `python my_bot.py`.
3.  When prompted, enter your WhatsApp phone number (including the country code, without `+` or `00`).
4.  You will receive a pairing code in the terminal.
5.  On your phone, go to **WhatsApp > Settings > Linked Devices > Link a device > Link with phone number instead** and enter the code.
6.  Your bot will connect and be ready!

## Simple Echo Bot Example

Here is a complete example of a bot that replies to any message it receives.

```python
# echo_bot.py
import asyncio
from pywabot import PyWaBot

# --- Configuration ---
SESSION_NAME = "echo_bot_session"
API_KEY = "your_api_key"

# Initialize the bot
bot = PyWaBot(session_name=SESSION_NAME, api_key=API_KEY)

@bot.on_message
async def echo_handler(message):
    """This handler is triggered for any incoming message."""
    # Ignore messages sent by the bot itself
    if message.from_me:
        return

    print(f"Received message from {message.sender_name}: '{message.text}'")
    
    # Formulate a reply
    reply_text = f"You said: '{message.text}'"
    
    # Simulate typing and send the reply
    await bot.typing(message.chat, duration=1)
    await bot.send_message(message.chat, reply_text, reply_chat=message)
    print(f"Sent reply to {message.sender_name}")

async def main():
    """Connects the bot and starts listening for messages."""
    print("Connecting echo bot...")
    if await bot.connect():
        print("Echo bot connected and listening!")
        await bot.start_listening()
    else:
        print("Failed to connect. Please run the connection script first to pair your device.")

if __name__ == "__main__":
    asyncio.run(main())
```

## Session Management

You can programmatically manage your bot's sessions.

### List Active Sessions

To see all sessions currently running on the server under your API key:

```python
import asyncio
from pywabot import PyWaBot

API_KEY = "your_api_key"

async def list_active_sessions():
    """Fetches and prints all active session names."""
    print("Listing active sessions...")
    try:
        sessions = await PyWaBot.list_sessions(api_key=API_KEY)
        if sessions:
            print("Found active sessions:")
            for session_name in sessions:
                print(f"- {session_name}")
        else:
            print("No active sessions found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(list_active_sessions())
```

### Delete a Session

To log out and delete a specific session from the server:

```python
import asyncio
from pywabot import PyWaBot

API_KEY = "your_api_key"
SESSION_TO_DELETE = "my_first_bot" # The name of the session you want to delete

async def delete_a_session():
    """Deletes a specified session from the server."""
    print(f"Attempting to delete session: '{SESSION_TO_DELETE}'...")
    try:
        success = await PyWaBot.delete_session(SESSION_TO_DELETE, api_key=API_KEY)
        if success:
            print(f"Session '{SESSION_TO_DELETE}' was successfully deleted.")
        else:
            print(f"Failed to delete session '{SESSION_TO_DELETE}'. It may not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(delete_a_session())
```

## More Examples

This library can do much more! For detailed examples on sending images, videos, GIFs, managing groups, handling media, and more, please check out the files in the `examples/` directory of this project.

## Support & Community

For questions, support, or to connect with other developers, join our community:

[**Get Support on Lynk.id**](http://lynk.id/khazulys/s/qewrnvwlm48d)

## Disclaimer

This is an unofficial library and is not affiliated with, authorized, maintained, sponsored, or endorsed by WhatsApp or Meta. Please use it responsibly and in accordance with WhatsApp's Terms of Service.

## License

This project is licensed under the MIT License.