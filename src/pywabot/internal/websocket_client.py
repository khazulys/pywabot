"""WebSocket client for handling real-time communication with the server."""

import asyncio
import json
import logging
from urllib.parse import urlencode

import websockets  # pylint: disable=import-error

logger = logging.getLogger(__name__)


async def listen_for_messages(
    base_websocket_url, api_key, session_name, on_message_callback
):
    """
    Connects to the WebSocket server and listens for incoming messages.
    """
    params = urlencode({'apiKey': api_key, 'sessionName': session_name})
    websocket_url = f"{base_websocket_url}/?{params}"

    logger.info("Attempting to connect to WebSocket URL: %s/", base_websocket_url)

    while True:
        try:
            async with websockets.connect(websocket_url) as websocket:
                logger.info("WebSocket connection established successfully.")
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        # Handle cases where the message is double-encoded JSON
                        if isinstance(data, str):
                            try:
                                data = json.loads(data)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "Could not decode inner JSON string: %s", data
                                )
                                continue  # Skip malformed message

                        # Ensure data is a dict and has the expected structure
                        if (
                            isinstance(data, dict)
                            and 'messages' in data
                            and data['messages']
                        ):
                            await on_message_callback(data)
                        else:
                            logger.debug(
                                "Received non-message data or empty message list: %s",
                                data,
                            )

                    except json.JSONDecodeError:
                        logger.error(
                            "Failed to decode WebSocket message as JSON: %s", message
                        )
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(
                            "WebSocket connection closed unexpectedly. Reconnecting..."
                        )
                        break
                    except (TypeError, KeyError) as e:
                        # Catch specific errors during message processing
                        logger.error("Error processing WebSocket message: %s", e)

        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(
                "Server rejected WebSocket connection: HTTP %s. "
                "Reconnecting in 5 seconds...",
                e.status_code,
            )
        except (
            ConnectionRefusedError,
            ConnectionResetError,
            OSError,
            websockets.exceptions.WebSocketException,
        ) as e:
            logger.error(
                "A WebSocket connection error occurred: %s. "
                "Reconnecting in 5 seconds...",
                e,
            )

        await asyncio.sleep(5)
