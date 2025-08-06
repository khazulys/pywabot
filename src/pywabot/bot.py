import os
import asyncio
import time
import logging
import base64
from .internal import api_client, websocket_client
from . import types
from .exceptions import ConnectionError

logger = logging.getLogger(__name__)

ENCODED_URL = 'GA0DERFVW3ARBAoeAA0sRgQJGVQEBBAZES1eFREdAQE8HwwWHlcCEUwdFTYfEgILSxUvGw=='
XOR_KEY = 'pywabot_secret_key'

def _get_api_url():
    try:
        encrypted_url_bytes = base64.b64decode(ENCODED_URL)
        
        key_bytes = XOR_KEY.encode('utf-8')
        decrypted_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_url_bytes)])
        
        decrypted_url = decrypted_bytes.decode('utf-8')
        
        logger.debug(f"Decryption attempt resulted in URL: '{decrypted_url}'")

        if not decrypted_url.startswith('http'):
            logger.warning(f"Decryption resulted in an invalid URL ('{decrypted_url}'). Falling back to default.")
            raise ValueError("Decrypted URL is not a valid HTTP/S link.")
            
        return decrypted_url
    except Exception as e:
        logger.error(f"Failed to decode or validate the API URL: {e}. Falling back to default.")


class PyWaBot:
    """
    An asynchronous Python wrapper for the Baileys WhatsApp API.
    ...    """
    def __init__(self, session_name, api_key, handle_media=True):
        """
        Initializes the PyWaBot instance.

        Args:
            session_name (str): The name for the WhatsApp session. This is required
                to differentiate between multiple bot instances.
            api_key (str): The API key for authentication.
            handle_media (bool): If True, the bot will automatically reply with
                informative messages for media content like images, locations, etc.
                Set to False to disable this behavior.

        Raises:
            ValueError: If `session_name` or `api_key` is not provided.
        """
        if not session_name:
            raise ValueError("A session_name must be provided.")
        if not api_key:
            raise ValueError("An api_key must be provided.")
            
        os.environ["PYWABOT_API_KEY"] = api_key
        self.session_name = session_name
        self.api_url = _get_api_url()
        self.api_key = api_key
        self.handle_media = handle_media
            
        self.websocket_url = self.api_url.replace('https', 'wss')
        self.is_connected = False
        self._command_handlers = {}
        self._default_handler = None

    def handle_msg(self, command):
        """
        A decorator to register a handler for a specific command.
        """
        def decorator(func):
            self._command_handlers[command] = func
            return func
        return decorator
    
    def on_message(self, func):
        """
        A decorator to register a default handler for any incoming message.
        """
        self._default_handler = func
        return func

    async def _handle_media_message(self, msg: types.WaMessage):
        """Sends an informative reply for various media types."""
        reply_text = ""
        if msg.image:
            caption = msg.image.get('caption', 'No caption')
            reply_text = f"🖼️ *Image Received*\n\n- *Caption:* {caption}\n- *Mimetype:* {msg.image.get('mimetype')}"
        elif msg.video:
            caption = msg.video.get('caption', 'No caption')
            reply_text = f"📹 *Video Received*\n\n- *Caption:* {caption}\n- *Duration:* {msg.video.get('seconds')}s"
        elif msg.audio:
            reply_text = f"🎵 *Audio Received*\n\n- *Type:* {'Voice Note' if msg.audio.get('ptt') else 'Audio File'}\n- *Duration:* {msg.audio.get('seconds')}s"
        elif msg.document:
            reply_text = f"📄 *Document Received*\n\n- *Filename:* {msg.document.get('fileName')}\n- *Mimetype:* {msg.document.get('mimetype')}"
        elif msg.location:
            loc = msg.get_location()
            maps_url = f"https://maps.google.com/?q={loc['latitude']},{loc['longitude']}"
            reply_text = f"📍 *Location Received*\n\n- *Coordinates:* {loc['latitude']:.5f}, {loc['longitude']:.5f}\n- *Details:* {loc.get('comment') or 'N/A'}\n- *View on Maps:* {maps_url}"
        elif msg.live_location:
            live_loc = msg.get_live_location()
            maps_url = f"https://maps.google.com/?q={live_loc['latitude']},{live_loc['longitude']}"
            reply_text = f"🛰️ *Live Location Update*\n\n- *Caption:* {live_loc.get('caption') or 'N/A'}\n- *Speed:* {live_loc.get('speed', 0):.2f} m/s\n- *View on Maps:* {maps_url}"

        if reply_text:
            await self.send_message(msg.chat, reply_text, reply_chat=msg)

    async def _process_incoming_message(self, raw_message):
        """Processes incoming raw messages from the WebSocket."""
        msg = types.WaMessage(raw_message)
        if msg.from_me:
            return
        
        handler_found = False
        # Command handling
        if msg.text:
            clean_text = msg.text.strip()
            for command, handler in self._command_handlers.items():
                if clean_text.startswith(command):
                    await handler(self, msg)
                    handler_found = True
                    break
        
        # If no command handler was found, check for media or default handler
        if not handler_found:
            is_media = any([msg.image, msg.video, msg.audio, msg.document, msg.location, msg.live_location])
            
            # If it's media and the feature is enabled, handle it
            if is_media and self.handle_media:
                await self._handle_media_message(msg)
                handler_found = True

            # If still no handler was found (e.g., plain text with no command), use default
            if not handler_found and self._default_handler:
                await self._default_default_handler(self, msg)
    
    async def connect(self):
        """
        Connects to the Baileys server and establishes a WhatsApp session.

        It checks the server status, starts a new session if one isn't active,
        and waits for the connection to be established.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        server_status = await api_client.get_server_status(self.api_url)
        if server_status == 'server_offline':
            return False
        if server_status == 'connected':
            self.is_connected = True
            return True
        
        success, message = await api_client.start_server_session(self.api_url, self.session_name)
        if not success:
            return False

        return await self.wait_for_connection(timeout=15)

    async def request_pairing_code(self, phone_number):
        """
        Requests a pairing code for linking a new device.
        """
        if self.is_connected:
            logger.warning("Cannot request pairing code, bot is already connected.")
            return None
        return await api_client.request_pairing_code(self.api_url, phone_number, self.session_name)

    async def wait_for_connection(self, timeout=60):
        """
        Waits for the WhatsApp connection to be established.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = await api_client.get_server_status(self.api_url)
                if status == 'connected':
                    self.is_connected = True
                    return True
                if status == 'server_offline':
                    return False
            except ConnectionError:
                pass  # Ignore and retry
            await asyncio.sleep(2)
        self.is_connected = False
        return False
    
    async def send_message(self, recipient_jid, text, reply_chat=None, mentions=None):
        """
        Sends a text message to a specified JID.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        response = await api_client.send_message_to_server(self.api_url, recipient_jid, text, reply_chat, mentions)
        return response.get('data') if response and response.get('success') else None
    
    async def send_mention(self, jid, text, mentions, reply_chat=None):
        """
        A convenience method to send a message with mentions.
        """
        return await self.send_message(jid, text, reply_chat=reply_chat, mentions=mentions)
    
    async def send_message_mention_all(self, jid, text, batch_size=50, delay=2):
        """
        Sends a message mentioning all participants in a group chat.
        """
        if not self.is_connected or not jid.endswith('@g.us'):
            return False
            
        metadata = await self.get_group_metadata(jid)
        if not metadata or not metadata.get('participants'):
            return False
            
        participant_jids = [p['id'] for p in metadata.get('participants', []) if p.get('id')]
        if not participant_jids:
            return False

        for i in range(0, len(participant_jids), batch_size):
            batch_jids = participant_jids[i:i + batch_size]
            mention_text = " ".join([f"@{jid.split('@')[0]}" for jid in batch_jids])
            full_text = f"{text}\n\n{mention_text.strip()}"

            await self.typing(jid, duration=1)
            await self.send_message(jid, full_text, mentions=batch_jids)
            logger.info(f"Sent mention batch to {len(batch_jids)} members.")
            
            if i + batch_size < len(participant_jids):
                await asyncio.sleep(delay)
        return True

    async def typing(self, jid, duration=1.0):
        """
        Simulates 'typing...' presence in a chat for a given duration.
        """
        if not self.is_connected: return
        await api_client.update_presence_on_server(self.api_url, jid, 'composing')
        await asyncio.sleep(duration)
        await api_client.update_presence_on_server(self.api_url, jid, 'paused')

    async def get_group_metadata(self, jid):
        """
        Retrieves metadata for a specific group.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        return await api_client.get_group_metadata(self.api_url, jid)

    async def forward_msg(self, recipient_jid, message_to_forward):
        """
        Forwards a given message to a recipient.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        if not message_to_forward or not message_to_forward._msg_info:
            return False
        return await api_client.forward_message_to_server(self.api_url, recipient_jid, message_to_forward._msg_info)

    async def edit_msg(self, recipient_jid, message_id, new_text):
        """
        Edits a message that was previously sent by the bot.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        return await api_client.edit_message_on_server(self.api_url, recipient_jid, message_id, new_text)

    async def mark_chat_as_read(self, message):
        """
        Marks a specific message's chat as read.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        return await api_client.update_chat_on_server(self.api_url, message.chat, 'read', message.raw['messages'][0])

    async def mark_chat_as_unread(self, jid):
        """
        Marks a chat as unread.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        return await api_client.update_chat_on_server(self.api_url, jid, 'unread')

    async def send_poll(self, recipient_jid, name, values):
        """
        Sends a poll message.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        response = await api_client.send_poll_to_server(self.api_url, recipient_jid, name, values)
        return response.get('data') if response and response.get('success') else None

    async def download_media(self, message, path='.'):
        """
        Downloads media (image, video, audio, document) from a message.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        media_message = message.image or message.video or message.audio or message.document
        if not media_message: return None

        media_data = await api_client.download_media_from_server(self.api_url, message.raw['messages'][0])
        if media_data:
            filename = media_message.get('fileName') or f"{message.id}.{media_message.get('mimetype').split('/')[1]}"
            filepath = os.path.join(path, filename)
            with open(filepath, 'wb') as f:
                f.write(media_data)
            return filepath
        return None

    async def send_reaction(self, message, emoji):
        """
        Sends a reaction to a specific message.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        return await api_client.send_reaction_to_server(
            self.api_url, message.chat, message.id, message.from_me, emoji
        )

    async def update_group_participants(self, jid, action, participants):
        """
        Updates group participants (add, remove, promote, demote).
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        return await api_client.update_group_participants(self.api_url, jid, action, participants)

    async def send_link_preview(self, recipient_jid, url, text):
        """
        Sends a message with a link preview.
        """
        if not self.is_connected: raise ConnectionError("Bot is not connected.")
        response = await api_client.send_link_preview_to_server(self.api_url, recipient_jid, url, text)
        return response.get('data') if response and response.get('success') else None

    async def send_gif(self, recipient_jid, url, caption=None):
        """
        Sends a GIF message.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        gif = types.Gif(url=url, caption=caption)
        response = await api_client.send_gif_to_server(self.api_url, recipient_jid, gif)
        return response.get('data') if response and response.get('success') else None

    async def send_image(self, recipient_jid, url, caption=None):
        """
        Sends an image message.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        image = types.Image(url=url, caption=caption)
        response = await api_client.send_image_to_server(self.api_url, recipient_jid, image)
        return response.get('data') if response and response.get('success') else None

    async def send_audio(self, recipient_jid, url, mimetype='audio/mp4'):
        """
        Sends an audio message with a specific mimetype.

        Args:
            recipient_jid (str): The JID of the recipient.
            url (str): A publicly accessible URL to the audio file.
            mimetype (str): The mimetype of the audio. Crucial for compatibility.
                          Examples: 'audio/mp4', 'audio/aac', 'audio/ogg; codecs=opus'.
                          Defaults to 'audio/mp4'.

        Raises:
            ValueError: If the URL is invalid or the mimetype is not an audio type.
            ConnectionError: If the bot is not connected.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        
        if not url or not url.startswith(('http://', 'https://')):
            logger.error(f"Invalid audio URL provided: {url}. URL must be publicly accessible.")
            raise ValueError("Audio URL must be a valid and publicly accessible http/https URL.")

        if not mimetype or not mimetype.startswith('audio/'):
            logger.error(f"Invalid mimetype for audio: '{mimetype}'. It must start with 'audio/'.")
            raise ValueError("Invalid mimetype. Must be an audio type (e.g., 'audio/mp4').")

        audio = types.Audio(url=url, mimetype=mimetype)
        logger.info(f"Attempting to send audio from URL: {url} with mimetype: {mimetype} to {recipient_jid}")
        
        response = await api_client.send_audio_to_server(self.api_url, recipient_jid, audio)
        return response.get('data') if response and response.get('success') else None

    async def send_video(self, recipient_jid, url, caption=None):
        """
        Sends a video message.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        video = types.Video(url=url, caption=caption)
        response = await api_client.send_video_to_server(self.api_url, recipient_jid, video)
        return response.get('data') if response and response.get('success') else None

    async def pin_chat(self, jid):
        """
        Pins a chat to the top of the chat list.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        return await api_client.pin_unpin_chat_on_server(self.api_url, jid, True)

    async def unpin_chat(self, jid):
        """
        Unpins a chat from the top of the chat list.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        return await api_client.pin_unpin_chat_on_server(self.api_url, jid, False)

    async def create_group(self, title, participants):
        """
        Creates a new group with the given title and participants.
        """
        if not self.is_connected:
            raise ConnectionError("Bot is not connected.")
        return await api_client.create_group_on_server(self.api_url, title, participants)

    @staticmethod
    async def list_sessions(api_key):
        """
        Lists all available sessions on the Baileys API server.
        """
        if not api_key:
            raise ValueError("An api_key must be provided.")
        os.environ["PYWABOT_API_KEY"] = api_key
        api_url = _get_api_url()
        return await api_client.list_sessions(api_url)

    @staticmethod
    async def delete_session(session_name, api_key):
        """
        Deletes a specific session from the server.
        """
        if not api_key:
            raise ValueError("An api_key must be provided.")
        os.environ["PYWABOT_API_KEY"] = api_key
        api_url = _get_api_url()
        logger.info(f"Requesting deletion of session: {session_name}")
        return await api_client.delete_session(api_url, session_name)

    async def start_listening(self):
        """
        Starts listening for incoming messages via WebSocket.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot start listening, bot is not connected.")
        await websocket_client.listen_for_messages(
            self.websocket_url, 
            self.api_key,
            self.session_name,
            self._process_incoming_message
        )