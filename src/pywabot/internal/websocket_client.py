import websockets
import asyncio
import json
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

async def listen_for_messages(base_websocket_url, api_key, session_name, on_message_callback):
    """
    Connects to the WebSocket server and listens for incoming messages.
    """
    params = urlencode({'apiKey': api_key, 'sessionName': session_name})
    websocket_url = f"{base_websocket_url}/?{params}"
    
    logger.info(f"Attempting to connect to WebSocket URL: {base_websocket_url}/")

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
                                logger.warning(f"Could not decode inner JSON string: {data}")
                                continue # Skip malformed message

                        # Ensure the data is a dict and has the expected structure
                        if isinstance(data, dict) and 'messages' in data and data['messages']:
                            await on_message_callback(data)
                        else:
                            logger.debug(f"Received non-message data or empty message list: {data}")

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode WebSocket message as JSON: {message}")
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed unexpectedly. Reconnecting...")
                        break
                    except Exception as e:
                        # Catch any other errors during message processing
                        logger.error(f"Error processing WebSocket message: {e}")

        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"Server rejected WebSocket connection: HTTP {e.status_code}. Reconnecting in 5 seconds...")
        except ConnectionRefusedError:
            logger.error("WebSocket connection refused. Is the server running? Reconnecting in 5 seconds...")
        except Exception as e:
            logger.error(f"An unexpected WebSocket error occurred: {e}. Reconnecting in 5 seconds...")
        
        await asyncio.sleep(5)