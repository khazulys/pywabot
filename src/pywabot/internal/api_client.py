"""
This module provides an asynchronous client for interacting with the Baileys API.

It handles request creation, authentication, and error handling for all
API endpoints used by the PyWaBot library.
"""
import json
import logging
import os

import httpx  # pylint: disable=import-error

from ..exceptions import (
    APIError,
    AuthenticationError,
    APIKeyMissingError,
    PyWaBotConnectionError,
)

logger = logging.getLogger(__name__)


def _get_api_client(**kwargs):
    """
    Creates and configures an httpx.AsyncClient with the necessary API key.

    Args:
        **kwargs: Additional keyword arguments to pass to the AsyncClient.

    Returns:
        httpx.AsyncClient: A configured asynchronous HTTP client.

    Raises:
        APIKeyMissingError: If the PYWABOT_API_KEY environment variable is not set.
    """
    api_key = os.environ.get("PYWABOT_API_KEY")
    if not api_key:
        raise APIKeyMissingError(
            "API Key not found. Please set the PYWABOT_API_KEY environment variable."
        )
    headers = {"X-API-Key": api_key}
    return httpx.AsyncClient(headers=headers, **kwargs)


async def _make_request(client, method, url, **kwargs):
    """
    Makes an API request and handles responses and errors.

    Args:
        client (httpx.AsyncClient): The HTTP client to use for the request.
        method (str): The HTTP method (e.g., 'get', 'post').
        url (str): The URL for the request.
        **kwargs: Additional keyword arguments for the request.

    Returns:
        Optional[Dict[str, Any]]: The JSON response from the API, or None.

    Raises:
        AuthenticationError: For 401 or 403 status codes.
        APIError: For other HTTP status errors.
        PyWaBotConnectionError: For network-related errors.
    """
    try:
        logger.debug("Making API request: %s %s", method.upper(), url)
        if 'json' in kwargs:
            logger.debug(
                "Request payload: %s", json.dumps(kwargs['json'], indent=2)
            )

        response = await client.request(method, url, **kwargs)
        logger.debug("Received API response: Status %d", response.status_code)
        response.raise_for_status()

        if response.status_code == 204:
            logger.debug("Response has no content.")
            return None

        logger.debug("Raw response text: %s", response.text)
        return response.json()
    except httpx.HTTPStatusError as e:
        error_message = e.response.text
        try:
            response_data = e.response.json()
            error_message = response_data.get('message', e.response.text)
        except json.JSONDecodeError:
            # Response is not valid JSON, use the raw text
            pass

        logger.error(
            "API request failed: Status %d - %s",
            e.response.status_code,
            error_message,
        )

        if e.response.status_code in [401, 403]:
            raise AuthenticationError(
                error_message, status_code=e.response.status_code
            ) from e
        raise APIError(
            error_message, status_code=e.response.status_code
        ) from e
    except httpx.RequestError as e:
        raise PyWaBotConnectionError(f"Failed to connect to the API: {e}") from e


async def start_server_session(api_url, session_name):
    """
    Starts a new session on the Baileys server.

    Args:
        api_url (str): The base URL of the API server.
        session_name (str): The name for the new session.

    Returns:
        Tuple[bool, str]: A tuple of success status and a message.
    """
    async with _get_api_client() as client:
        try:
            payload = {"sessionName": session_name}
            await _make_request(
                client, "post", f"{api_url}/start-session", json=payload
            )
            return True, "Session initialized successfully."
        except APIError as e:
            if e.status_code == 400 and "already active" in e.message:
                return True, "A session is already active."
            raise
        except PyWaBotConnectionError as e:
            return False, str(e)


async def get_server_status(api_url):
    """
    Retrieves the status of the Baileys server.

    Args:
        api_url (str): The base URL of the API server.

    Returns:
        Optional[str]: The server status (e.g., 'connected') or 'server_offline'.
    """
    try:
        async with _get_api_client() as client:
            data = await _make_request(client, "get", f"{api_url}/status")
            return data.get('status') if data else 'server_offline'
    except (PyWaBotConnectionError, APIKeyMissingError):
        return 'server_offline'


async def request_pairing_code(api_url, phone_number, session_name):
    """
    Requests a pairing code for a new device.

    Args:
        api_url (str): The base URL of the API server.
        phone_number (str): The phone number to pair.
        session_name (str): The session name to associate with the pairing.

    Returns:
        Optional[str]: The pairing code if successful, otherwise None.
    """
    async with _get_api_client(timeout=120.0) as client:
        payload = {"number": phone_number, "sessionName": session_name}
        data = await _make_request(
            client, "post", f"{api_url}/pair-code", json=payload
        )
        return data.get('code') if data else None


async def send_message_to_server(
    api_url, number, message, reply_chat=None, mentions=None
):
    """
    Sends a text message via the API.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        message (str): The text message to send.
        reply_chat (Optional[WaMessage]): The message to reply to.
        mentions (Optional[List[str]]): A list of JIDs to mention.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client(timeout=30.0) as client:
        payload = {"number": number, "message": message}
        if (
            reply_chat
            and 'messages' in reply_chat.raw
            and reply_chat.raw['messages']
        ):
            payload["quotedMessage"] = reply_chat.raw['messages'][0]
        if mentions:
            payload["mentions"] = mentions
        return await _make_request(
            client, "post", f"{api_url}/send-message", json=payload
        )


async def update_presence_on_server(api_url, jid, state):
    """
    Updates the bot's presence status (e.g., 'composing').

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The chat JID where the presence is updated.
        state (str): The presence state ('composing', 'paused', etc.).

    Returns:
        bool: True if the update was successful.
    """
    async with _get_api_client() as client:
        payload = {"jid": jid, "state": state}
        await _make_request(
            client, "post", f"{api_url}/presence-update", json=payload
        )
        return True


async def get_group_metadata(api_url, jid):
    """
    Retrieves metadata for a specific group.

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The group's JID.

    Returns:
        Optional[Dict[str, Any]]: The group metadata.
    """
    async with _get_api_client() as client:
        return await _make_request(
            client, "get", f"{api_url}/group-metadata/{jid}"
        )


async def forward_message_to_server(api_url, jid, message_obj):
    """
    Forwards a message to a recipient.

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The recipient's JID.
        message_obj (Dict[str, Any]): The raw message object to forward.

    Returns:
        bool: True if the forward was successful.
    """
    async with _get_api_client() as client:
        payload = {"jid": jid, "message": message_obj}
        await _make_request(
            client, "post", f"{api_url}/forward-message", json=payload
        )
        return True


async def edit_message_on_server(api_url, jid, message_id, new_text):
    """
    Edits a previously sent message.

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The chat JID where the message is.
        message_id (str): The ID of the message to edit.
        new_text (str): The new text for the message.

    Returns:
        bool: True if the edit was successful.
    """
    async with _get_api_client() as client:
        payload = {"jid": jid, "messageId": message_id, "newText": new_text}
        await _make_request(
            client, "post", f"{api_url}/edit-message", json=payload
        )
        return True


async def update_chat_on_server(api_url, jid, action, message=None):
    """
    Updates a chat's state (e.g., 'read', 'unread').

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The chat JID to update.
        action (str): The action to perform ('read', 'unread', etc.).
        message (Optional[Dict[str, Any]]): The message object for context.

    Returns:
        bool: True if the update was successful.
    """
    async with _get_api_client() as client:
        payload = {"jid": jid, "action": action}
        if message:
            payload["message"] = message
        await _make_request(
            client, "post", f"{api_url}/chat/update", json=payload
        )
        return True


async def send_poll_to_server(api_url, number, name, values):
    """
    Sends a poll message.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        name (str): The name/question of the poll.
        values (List[str]): The options for the poll.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client() as client:
        payload = {"number": number, "name": name, "values": values}
        return await _make_request(
            client, "post", f"{api_url}/send-poll", json=payload
        )


async def download_media_from_server(api_url, message):
    """
    Downloads media from a message.

    Args:
        api_url (str): The base URL of the API server.
        message (Dict[str, Any]): The raw message object containing the media.

    Returns:
        Optional[bytes]: The raw media data as bytes.

    Raises:
        PyWaBotConnectionError: If the download fails due to a network error.
    """
    try:
        async with _get_api_client() as client:
            payload = {"message": message}
            response = await client.post(
                f"{api_url}/download-media", json=payload
            )
            response.raise_for_status()
            return response.content
    except httpx.RequestError as e:
        raise PyWaBotConnectionError(f"Failed to download media: {e}") from e


async def send_reaction_to_server(api_url, jid, message_id, from_me, emoji):
    """
    Sends a reaction to a message.

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The chat JID where the message is.
        message_id (str): The ID of the message to react to.
        from_me (bool): Whether the message was sent by the bot.
        emoji (str): The emoji to react with.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client() as client:
        payload = {
            "jid": jid,
            "messageId": message_id,
            "fromMe": from_me,
            "emoji": emoji,
        }
        return await _make_request(
            client, "post", f"{api_url}/send-reaction", json=payload
        )


async def update_group_participants(api_url, jid, action, participants):
    """
    Updates participants in a group (add, remove, etc.).

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The group's JID.
        action (str): The action to perform ('add', 'remove', 'promote').
        participants (List[str]): A list of participant JIDs.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client() as client:
        payload = {
            "jid": jid,
            "action": action,
            "participants": participants,
        }
        return await _make_request(
            client, "post", f"{api_url}/group-participants-update", json=payload
        )


async def send_link_preview_to_server(api_url, number, url, text):
    """
    Sends a message with a link preview.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        url (str): The URL to preview.
        text (str): The text to send with the preview.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client() as client:
        payload = {"number": number, "url": url, "text": text}
        return await _make_request(
            client, "post", f"{api_url}/send-link-preview", json=payload
        )


async def send_gif_to_server(api_url, number, gif):
    """
    Sends a GIF message.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        gif (types.Gif): The GIF object to send.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client(timeout=30.0) as client:
        payload = {
            "number": number,
            "message": {
                "video": {"url": gif.url},
                "caption": gif.caption,
                "gifPlayback": True,
            },
        }
        return await _make_request(
            client, "post", f"{api_url}/send-message", json=payload
        )


async def send_image_to_server(api_url, number, image):
    """
    Sends an image message.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        image (types.Image): The image object to send.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client(timeout=30.0) as client:
        payload = {
            "number": number,
            "message": {
                "image": {"url": image.url},
                "caption": image.caption,
            },
        }
        return await _make_request(
            client, "post", f"{api_url}/send-message", json=payload
        )


async def send_audio_to_server(api_url, number, audio):
    """
    Sends an audio message.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        audio (types.Audio): The audio object to send.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client(timeout=30.0) as client:
        payload = {
            "number": number,
            "message": {
                "audio": {"url": audio.url},
                "mimetype": audio.mimetype,
            },
        }
        return await _make_request(
            client, "post", f"{api_url}/send-message", json=payload
        )


async def send_video_to_server(api_url, number, video):
    """
    Sends a video message.

    Args:
        api_url (str): The base URL of the API server.
        number (str): The recipient's JID.
        video (types.Video): The video object to send.

    Returns:
        Optional[Dict[str, Any]]: The API response data.
    """
    async with _get_api_client(timeout=60.0) as client:
        payload = {
            "number": number,
            "message": {
                "video": {"url": video.url},
                "caption": video.caption,
            },
        }
        return await _make_request(
            client, "post", f"{api_url}/send-message", json=payload
        )


async def pin_unpin_chat_on_server(api_url, jid, pin):
    """
    Pins or unpins a chat.

    Args:
        api_url (str): The base URL of the API server.
        jid (str): The chat JID to pin or unpin.
        pin (bool): True to pin, False to unpin.

    Returns:
        bool: True if the action was successful.
    """
    async with _get_api_client() as client:
        payload = {"jid": jid, "pin": pin}
        await _make_request(
            client, "post", f"{api_url}/chat/pin", json=payload
        )
        return True


async def create_group_on_server(api_url, title, participants):
    """
    Creates a new group.

    Args:
        api_url (str): The base URL of the API server.
        title (str): The title of the new group.
        participants (List[str]): A list of participant JIDs to add.

    Returns:
        Optional[Dict[str, Any]]: The API response data for the new group.
    """
    async with _get_api_client() as client:
        payload = {"title": title, "participants": participants}
        response = await _make_request(
            client, "post", f"{api_url}/group-create", json=payload
        )
        return (
            response.get('data')
            if response and response.get('success')
            else None
        )


async def list_sessions(api_url):
    """
    Lists all active sessions on the server.

    Args:
        api_url (str): The base URL of the API server.

    Returns:
        List[str]: A list of active session names.
    """
    async with _get_api_client() as client:
        response = await _make_request(client, "get", f"{api_url}/sessions")
        return response.get('sessions', []) if response else []


async def delete_session(api_url, session_name):
    """
    Deletes a session from the server.

    Args:
        api_url (str): The base URL of the API server.
        session_name (str): The name of the session to delete.

    Returns:
        bool: True if the deletion was successful.
    """
    async with _get_api_client() as client:
        response = await _make_request(
            client, "delete", f"{api_url}/sessions/{session_name}"
        )
        return response.get('success', False) if response else False
