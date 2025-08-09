"""
This module contains the main PyWaBot class for interacting with the WhatsApp API.
"""
import os
import asyncio
import time
import logging
import base64
import binascii
import inspect
import functools
from typing import Callable, Coroutine, Any, Dict, Optional, List

from .internal import api_client, websocket_client
from . import types
from .exceptions import PyWaBotConnectionError

# Type alias for handler functions for better readability
MessageHandler = Callable[..., Coroutine[Any, Any, None]]

logger = logging.getLogger(__name__)

ENCODED_URL = 'GA0DERFVW3ARBAoeAA0sRgQJGVQEBBAZES1eFREdAQE8HwwWHlcCEUwdFTYfEgILSxUvGw=='
XOR_KEY = 'pywabot_secret_key'


def _get_api_url() -> str:
    """
    Decrypts and returns the API URL.

    Returns:
        str: The decrypted API URL.

    Raises:
        ValueError: If the decrypted URL is invalid.
    """
    try:
        encrypted_url_bytes = base64.b64decode(ENCODED_URL)
        key_bytes = XOR_KEY.encode('utf-8')
        decrypted_bytes = bytes(
            [b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_url_bytes)]
        )
        decrypted_url = decrypted_bytes.decode('utf-8')

        logger.debug("Decryption attempt resulted in URL: '%s'", decrypted_url)

        if not decrypted_url.startswith('http'):
            logger.warning(
                "Decryption resulted in an invalid URL ('%s').", decrypted_url
            )
            raise ValueError("Decrypted URL is not a valid HTTP/S link.")

        return decrypted_url
    except (binascii.Error, ValueError) as e:
        logger.error("Failed to decode or validate the API URL: %s.", e)
        # Re-raise as a more generic error to avoid leaking implementation details
        raise ValueError("Could not determine a valid API URL.") from e


class PyWaBot:  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """
    An asynchronous Python wrapper for the Baileys WhatsApp API.
    """
    def __init__(self, session_name: str, api_key: str, handle_media: bool = True):
        """
        Initializes the PyWaBot instance.

        Args:
            session_name (str): The name for the WhatsApp session.
            api_key (str): The API key for authentication.
            handle_media (bool): If True, the bot will automatically reply to
                media messages. Set to False to disable this behavior.

        Raises:
            ValueError: If `session_name` or `api_key` is not provided.
        """
        if not session_name:
            raise ValueError("A session_name must be provided.")
        if not api_key:
            raise ValueError("An api_key must be provided.")

        self.session_name = session_name
        self.api_key = api_key
        self.handle_media = handle_media
        self.api_url = _get_api_url()

        # Create a session context for API calls
        self._session_context = api_client.SessionContext(
            api_url=self.api_url,
            api_key=self.api_key,
            session_name=self.session_name,
        )

        self.websocket_url = self.api_url.replace('https', 'wss')
        self.is_connected = False
        self._command_handlers: Dict[str, MessageHandler] = {}
        self._default_handler: Optional[MessageHandler] = None
        self._location_handler: Optional[MessageHandler] = None
        self._user_states: Dict[str, Any] = {}

    def set_user_state(self, chat_id: str, state: Any):
        """
        Sets the state for a specific user/chat.

        Args:
            chat_id (str): The chat JID (e.g., '6281234567890@s.whatsapp.net').
            state (Any): The state to set for the user. Can be a string, dict, etc.
        """
        self._user_states[chat_id] = state
        logger.debug("State set for %s: %s", chat_id, state)

    def get_user_state(self, chat_id: str) -> Optional[Any]:
        """
        Retrieves the state for a specific user/chat.

        Args:
            chat_id (str): The chat JID.

        Returns:
            The user's state, or None if no state is set.
        """
        return self._user_states.get(chat_id)

    def clear_user_state(self, chat_id: str) -> bool:
        """
        Clears the state for a specific user/chat.

        Args:
            chat_id (str): The chat JID.

        Returns:
            bool: True if a state was cleared, False otherwise.
        """
        if chat_id in self._user_states:
            del self._user_states[chat_id]
            logger.debug("State cleared for %s.", chat_id)
            return True
        return False

    def handle_msg(self, command: str) -> Callable[[MessageHandler], MessageHandler]:
        """
        A decorator to register a handler for a specific command.
        """
        def decorator(func: MessageHandler) -> MessageHandler:
            sig = inspect.signature(func)
            num_params = len(sig.parameters)

            if num_params not in [1, 2]:
                raise TypeError(
                    f"Handler for command '{command}' must accept 1 or 2 arguments, "
                    f"but it accepts {num_params}."
                )

            @functools.wraps(func)
            async def wrapper(_: Any, message: types.WaMessage) -> None:
                if num_params == 1:
                    await func(message)
                else:
                    await func(_, message)

            self._command_handlers[command] = wrapper
            return func
        return decorator

    def on_message(self, func: MessageHandler) -> MessageHandler:
        """
        A decorator to register a default handler for any incoming message.
        """
        sig = inspect.signature(func)
        num_params = len(sig.parameters)

        if num_params not in [1, 2]:
            raise TypeError(
                f"Default message handler must accept 1 or 2 arguments, "
                f"but it accepts {num_params}."
            )

        @functools.wraps(func)
        async def wrapper(_: Any, message: types.WaMessage) -> None:
            if num_params == 1:
                await func(message)
            else:
                await func(_, message)

        self._default_handler = wrapper
        return func

    def on_location(self, func: MessageHandler) -> MessageHandler:
        """
        A decorator to register a handler for incoming location messages.
        """
        sig = inspect.signature(func)
        num_params = len(sig.parameters)

        if num_params not in [1, 2]:
            raise TypeError(
                f"Location handler must accept 1 or 2 arguments, "
                f"but it accepts {num_params}."
            )

        @functools.wraps(func)
        async def wrapper(_: Any, message: types.WaMessage) -> None:
            if num_params == 1:
                await func(message)
            else:
                await func(_, message)

        self._location_handler = wrapper
        return func

    async def _handle_media_message(self, msg: types.WaMessage):  # pylint: disable=too-many-locals
        """Sends an informative reply for various media types."""
        reply_text = ""
        if msg.image:
            caption = msg.image.get('caption', 'No caption')
            mimetype = msg.image.get('mimetype')
            reply_text = (
                f"🖼️ *Image Received*\n\n"
                f"- *Caption:* {caption}\n"
                f"- *Mimetype:* {mimetype}"
            )
        elif msg.video:
            caption = msg.video.get('caption', 'No caption')
            duration = msg.video.get('seconds')
            reply_text = (
                f"📹 *Video Received*\n\n"
                f"- *Caption:* {caption}\n"
                f"- *Duration:* {duration}s"
            )
        elif msg.audio:
            is_ptt = 'Voice Note' if msg.audio.get('ptt') else 'Audio File'
            duration = msg.audio.get('seconds')
            reply_text = (
                f"🎵 *Audio Received*\n\n"
                f"- *Type:* {is_ptt}\n"
                f"- *Duration:* {duration}s"
            )
        elif msg.document:
            filename = msg.document.get('fileName')
            mimetype = msg.document.get('mimetype')
            reply_text = (
                f"📄 *Document Received*\n\n"
                f"- *Filename:* {filename}\n"
                f"- *Mimetype:* {mimetype}"
            )
        elif msg.location:
            loc = msg.get_location()
            if loc:
                maps_url = (
                    f"https://maps.google.com/?q={loc['latitude']},"
                    f"{loc['longitude']}"
                )
                comment = loc.get('comment') or 'N/A'
                reply_text = (
                    f"📍 *Location Received*\n\n"
                    f"- *Coordinates:* {loc['latitude']:.5f}, {loc['longitude']:.5f}\n"
                    f"- *Details:* {comment}\n"
                    f"- *View on Maps:* {maps_url}"
                )
        elif msg.live_location:
            try:
                live_loc = msg.get_live_location()
                if live_loc:
                    lat = live_loc.get('latitude')
                    lon = live_loc.get('longitude')
                    maps_url = f"https://maps.google.com/?q={lat},{lon}" if lat and lon else "N/A"
                    caption = live_loc.get('caption') or 'N/A'
                    speed = live_loc.get('speed', 0)
                    reply_text = (
                        f"🛰️ *Live Location Update*\n\n"
                        f"- *Caption:* {caption}\n"
                        f"- *Speed:* {speed:.2f} m/s\n"
                        f"- *View on Maps:* {maps_url}"
                    )
            except (TypeError, KeyError) as e:
                logger.error("Error processing live location message: %s", e)

        if reply_text:
            await self.send_message(msg.chat, reply_text, reply_chat=msg)

    async def _process_incoming_message(self, raw_message: Dict[str, Any]):
        """Processes incoming raw messages from the WebSocket."""
        msg = types.WaMessage(raw_message)
        if msg.from_me:
            return

        handler_found = False
        if msg.text:
            clean_text = msg.text.strip()
            for command, handler in self._command_handlers.items():
                if clean_text.startswith(command):
                    await handler(self, msg)
                    handler_found = True
                    break
        if handler_found:
            return

        if msg.location and self._location_handler:
            await self._location_handler(self, msg)
            return

        is_media = any([
            msg.image, msg.video, msg.audio,
            msg.document, msg.location, msg.live_location
        ])
        if is_media and self.handle_media:
            await self._handle_media_message(msg)
            handler_found = True

        if not handler_found and self._default_handler:
            await self._default_handler(self, msg)

    async def connect(self) -> bool:
        """
        Connects to the Baileys server and establishes a WhatsApp session.
        """
        server_status = await api_client.get_server_status(self._session_context)
        if server_status == 'offline':
            success, _ = await api_client.start_server_session(self._session_context)
            if not success:
                return False
            return await self.wait_for_connection(timeout=15)

        if server_status == 'connected':
            self.is_connected = True
            return True

        return await self.wait_for_connection(timeout=15)

    async def request_pairing_code(self, phone_number: str) -> Optional[str]:
        """Requests a pairing code for linking a new device."""
        if self.is_connected:
            logger.warning(
                "Cannot request pairing code, bot is already connected."
            )
            return None
        return await api_client.request_pairing_code(
            self._session_context, phone_number
        )

    async def wait_for_connection(self, timeout: int = 60) -> bool:
        """Waits for the WhatsApp connection to be established."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = await api_client.get_server_status(self._session_context)
                if status == 'connected':
                    self.is_connected = True
                    return True
                if status == 'server_offline':
                    return False
            except PyWaBotConnectionError:
                pass
            await asyncio.sleep(2)
        self.is_connected = False
        return False

    async def send_message(
        self,
        recipient_jid: str,
        text: str,
        reply_chat: Optional[types.WaMessage] = None,
        mentions: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Sends a text message to a specified JID."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        response = await api_client.send_message_to_server(
            self._session_context, recipient_jid, text, reply_chat, mentions
        )
        return response.get('data') if response and response.get('success') else None

    async def send_mention(
        self,
        jid: str,
        text: str,
        mentions: List[str],
        reply_chat: Optional[types.WaMessage] = None
    ) -> Optional[Dict[str, Any]]:
        """A convenience method to send a message with mentions."""
        return await self.send_message(
            jid, text, reply_chat=reply_chat, mentions=mentions
        )

    async def send_message_mention_all(
        self, jid: str, text: str, batch_size: int = 50, delay: int = 2
    ) -> bool:
        """Sends a message mentioning all participants in a group chat."""
        if not self.is_connected or not jid.endswith('@g.us'):
            return False

        metadata = await self.get_group_metadata(jid)
        if not metadata or not metadata.get('participants'):
            return False

        participant_jids = [
            p['id'] for p in metadata.get('participants', []) if p.get('id')
        ]
        if not participant_jids:
            return False

        for i in range(0, len(participant_jids), batch_size):
            batch_jids = participant_jids[i:i + batch_size]
            mention_text = " ".join([f"@{p_jid.split('@')[0]}" for p_jid in batch_jids])
            full_text = f"{text}\n\n{mention_text.strip()}"

            await self.typing(jid, duration=1)
            await self.send_message(jid, full_text, mentions=batch_jids)
            logger.info("Sent mention batch to %d members.", len(batch_jids))

            if i + batch_size < len(participant_jids):
                await asyncio.sleep(delay)
        return True

    async def typing(self, jid: str, duration: float = 1.0) -> None:
        """Simulates 'typing...' presence in a chat for a given duration."""
        if not self.is_connected:
            return
        await api_client.update_presence_on_server(
            self._session_context, jid, 'composing'
        )
        await asyncio.sleep(duration)
        await api_client.update_presence_on_server(
            self._session_context, jid, 'paused'
        )

    async def get_group_metadata(self, jid: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata for a specific group."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.get_group_metadata(self._session_context, jid)

    async def forward_msg(
        self,
        recipient_jid: str,
        message_to_forward: types.WaMessage
    ) -> bool:
        """Forwards a given message to a recipient."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        if not message_to_forward or not message_to_forward._msg_info:  # pylint: disable=protected-access
            return False
        return await api_client.forward_message_to_server(
            self._session_context,
            recipient_jid,
            message_to_forward._msg_info,  # pylint: disable=protected-access
        )

    async def edit_msg(self, recipient_jid: str, message_id: str, new_text: str) -> bool:
        """Edits a message that was previously sent by the bot."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.edit_message_on_server(
            self._session_context, recipient_jid, message_id, new_text
        )

    async def mark_chat_as_read(self, message: types.WaMessage) -> bool:
        """Marks a specific message's chat as read."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.update_chat_on_server(
            self._session_context,
            message.chat,
            'read',
            message.raw['messages'][0],
        )

    async def mark_chat_as_unread(self, jid: str) -> bool:
        """Marks a chat as unread."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.update_chat_on_server(
            self._session_context, jid, 'unread'
        )

    async def send_poll(
        self,
        recipient_jid: str,
        name: str,
        values: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Sends a poll message."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        response = await api_client.send_poll_to_server(
            self._session_context, recipient_jid, name, values
        )
        return response.get('data') if response and response.get('success') else None

    async def download_media(self, message: types.WaMessage, path: str = '.') -> Optional[str]:
        """Downloads media (image, video, audio, document) from a message."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        media_message = (
            message.image or message.video or message.audio or message.document
        )
        if not media_message:
            return None

        media_data = await api_client.download_media_from_server(
            self._session_context, message.raw['messages'][0]
        )
        if media_data:
            ext = media_message.get('mimetype').split('/')[1].split(';')[0]
            filename = media_message.get('fileName') or f"{message.id}.{ext}"
            filepath = os.path.join(path, filename)
            with open(filepath, 'wb') as f:
                f.write(media_data)
            return filepath
        return None

    async def send_reaction(self, message: types.WaMessage, emoji: str) -> bool:
        """Sends a reaction to a specific message."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.send_reaction_to_server(
            self._session_context,
            message.chat,
            message.id,
            message.from_me,
            emoji,
        )

    async def update_group_participants(
        self,
        jid: str,
        action: str,
        participants: List[str]
    ) -> bool:
        """Updates group participants (add, remove, promote, demote)."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.update_group_participants(
            self._session_context, jid, action, participants
        )

    async def send_link_preview(
        self,
        recipient_jid: str,
        url: str,
        text: str
    ) -> Optional[Dict[str, Any]]:
        """Sends a message with a link preview."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        response = await api_client.send_link_preview_to_server(
            self._session_context, recipient_jid, url, text
        )
        return response.get('data') if response and response.get('success') else None

    async def _send_media(
        self,
        recipient_jid: str,
        message_payload: Dict[str, Any],
        timeout: int,
    ) -> Optional[Dict[str, Any]]:
        """Internal helper to send media messages."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        response = await api_client.send_media_to_server(
            self._session_context,
            recipient_jid,
            message_payload,
            timeout,
        )
        return response.get('data') if response and response.get('success') else None

    async def send_gif(
        self,
        recipient_jid: str,
        url: str,
        caption: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Sends a GIF message."""
        message_payload = {
            "video": {"url": url},
            "caption": caption,
            "gifPlayback": True,
        }
        return await self._send_media(recipient_jid, message_payload, timeout=30)

    async def send_image(
        self,
        recipient_jid: str,
        url: str,
        caption: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Sends an image message."""
        message_payload = {"image": {"url": url}, "caption": caption}
        return await self._send_media(recipient_jid, message_payload, timeout=30)

    async def send_audio(
        self,
        recipient_jid: str,
        url: str,
        mimetype: str = 'audio/mp4'
    ) -> Optional[Dict[str, Any]]:
        """
        Sends an audio message with a specific mimetype.
        """
        if not url or not url.startswith(('http://', 'https://')):
            raise ValueError("URL must be a valid and publicly accessible.")
        if not mimetype or not mimetype.startswith('audio/'):
            raise ValueError("Invalid mimetype. Must be an audio type.")

        message_payload = {"audio": {"url": url}, "mimetype": mimetype}
        return await self._send_media(recipient_jid, message_payload, timeout=30)

    async def send_video(
        self,
        recipient_jid: str,
        url: str,
        caption: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Sends a video message."""
        message_payload = {"video": {"url": url}, "caption": caption}
        return await self._send_media(recipient_jid, message_payload, timeout=60)

    async def pin_chat(self, jid: str) -> bool:
        """Pins a chat to the top of the chat list."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.pin_unpin_chat_on_server(
            self._session_context, jid, True
        )

    async def unpin_chat(self, jid: str) -> bool:
        """Unpins a chat from the top of the chat list."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.pin_unpin_chat_on_server(
            self._session_context, jid, False
        )

    async def create_group(self, title: str, participants: List[str]) -> Optional[Dict[str, Any]]:
        """Creates a new group with the given title and participants."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Bot is not connected.")
        return await api_client.create_group_on_server(
            self._session_context, title, participants
        )

    @staticmethod
    async def list_sessions(api_key: str) -> Optional[Dict[str, Any]]:
        """Lists all available sessions on the Baileys API server."""
        if not api_key:
            raise ValueError("An api_key must be provided.")
        api_url = _get_api_url()
        if not api_url:
            return None
        return await api_client.list_sessions(api_url, api_key)

    @staticmethod
    async def delete_session(session_name: str, api_key: str) -> bool:
        """Deletes a specific session from the server."""
        if not api_key:
            raise ValueError("An api_key must be provided.")
        api_url = _get_api_url()
        if not api_url:
            return False
        logger.info("Requesting deletion of session: %s", session_name)
        return await api_client.delete_session(api_url, api_key, session_name)

    async def start_listening(self) -> None:
        """Starts listening for incoming messages via WebSocket."""
        if not self.is_connected:
            raise PyWaBotConnectionError("Cannot start listening, not connected.")
        await websocket_client.listen_for_messages(
            self.websocket_url,
            self.api_key,
            self.session_name,
            self._process_incoming_message
        )
