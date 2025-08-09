"""
This module provides an asynchronous client for interacting with the Baileys API.

It handles request creation, authentication, and error handling for all
API endpoints used by the PyWaBot library. This client is designed to be
stateless, requiring session information to be passed for each request
to ensure proper multi-session isolation.
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx  # pylint: disable=import-error

from ..exceptions import (
    APIError,
    AuthenticationError,
    APIKeyMissingError,
    PyWaBotConnectionError,
)
from .. import types

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """A data class to hold session-specific information."""
    api_url: str
    api_key: str
    session_name: str


def _get_api_client(api_key: str, **kwargs) -> httpx.AsyncClient:
    """
    Creates and configures an httpx.AsyncClient with the necessary API key.
    """
    if not api_key:
        raise APIKeyMissingError("An API Key must be provided for the request.")
    headers = {"X-API-Key": api_key}
    return httpx.AsyncClient(headers=headers, **kwargs)


async def _make_request(
    client: httpx.AsyncClient, method: str, url: str, **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Makes an API request and handles responses and errors.
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


async def start_server_session(
    context: SessionContext,
) -> Tuple[bool, str]:
    """Starts a new session on the Baileys server."""
    async with _get_api_client(context.api_key) as client:
        try:
            payload = {"sessionName": context.session_name}
            await _make_request(
                client, "post", f"{context.api_url}/sessions/start", json=payload
            )
            return True, "Session initialized successfully."
        except APIError as e:
            if e.status_code == 400 and "already active" in e.message:
                return True, "A session is already active."
            raise
        except PyWaBotConnectionError as e:
            return False, str(e)


async def get_server_status(context: SessionContext) -> str:
    """Retrieves the status of a specific session."""
    try:
        async with _get_api_client(context.api_key) as client:
            data = await _make_request(
                client, "get", f"{context.api_url}/sessions/{context.session_name}/status"
            )
            return data.get('status', 'offline') if data else 'offline'
    except (PyWaBotConnectionError, APIKeyMissingError, APIError):
        return 'offline'


async def request_pairing_code(
    context: SessionContext, phone_number: str
) -> Optional[str]:
    """Requests a pairing code for a new device."""
    async with _get_api_client(context.api_key, timeout=120.0) as client:
        payload = {"number": phone_number, "sessionName": context.session_name}
        data = await _make_request(
            client, "post", f"{context.api_url}/sessions/pair-code", json=payload
        )
        return data.get('code') if data else None


async def send_message_to_server(
    context: SessionContext,
    number: str,
    message: str,
    reply_chat: Optional[types.WaMessage] = None,
    mentions: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Sends a text message via the API for a specific session."""
    async with _get_api_client(context.api_key, timeout=30.0) as client:
        payload = {
            "sessionName": context.session_name,
            "number": number,
            "message": message,
        }
        if (
            reply_chat
            and 'messages' in reply_chat.raw
            and reply_chat.raw['messages']
        ):
            payload["quotedMessage"] = reply_chat.raw['messages'][0]
        if mentions:
            payload["mentions"] = mentions
        return await _make_request(
            client, "post", f"{context.api_url}/send/message", json=payload
        )


async def update_presence_on_server(
    context: SessionContext, jid: str, state: str
) -> bool:
    """Updates the bot's presence status for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {"sessionName": context.session_name, "jid": jid, "state": state}
        await _make_request(
            client, "post", f"{context.api_url}/presence/update", json=payload
        )
        return True


async def get_group_metadata(
    context: SessionContext, jid: str
) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a specific group for a specific session."""
    async with _get_api_client(context.api_key) as client:
        params = {"sessionName": context.session_name}
        return await _make_request(
            client, "get", f"{context.api_url}/groups/{jid}/metadata", params=params
        )


async def forward_message_to_server(
    context: SessionContext,
    jid: str,
    message_obj: Dict[str, Any],
) -> bool:
    """Forwards a message to a recipient for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "jid": jid,
            "message": message_obj,
        }
        await _make_request(
            client, "post", f"{context.api_url}/forward/message", json=payload
        )
        return True


async def edit_message_on_server(
    context: SessionContext,
    jid: str,
    message_id: str,
    new_text: str,
) -> bool:
    """Edits a previously sent message for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "jid": jid,
            "messageId": message_id,
            "newText": new_text,
        }
        await _make_request(
            client, "post", f"{context.api_url}/edit/message", json=payload
        )
        return True


async def update_chat_on_server(
    context: SessionContext,
    jid: str,
    action: str,
    message: Optional[Dict[str, Any]] = None,
) -> bool:
    """Updates a chat's state for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {"sessionName": context.session_name, "jid": jid, "action": action}
        if message:
            payload["message"] = message
        await _make_request(
            client, "post", f"{context.api_url}/chats/update", json=payload
        )
        return True


async def send_poll_to_server(
    context: SessionContext,
    number: str,
    name: str,
    values: List[str],
) -> Optional[Dict[str, Any]]:
    """Sends a poll message for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "number": number,
            "name": name,
            "values": values,
        }
        return await _make_request(
            client, "post", f"{context.api_url}/send/poll", json=payload
        )


async def download_media_from_server(
    context: SessionContext, message: Dict[str, Any]
) -> Optional[bytes]:
    """Downloads media from a message for a specific session."""
    try:
        async with _get_api_client(context.api_key) as client:
            payload = {"sessionName": context.session_name, "message": message}
            response = await client.post(
                f"{context.api_url}/download/media", json=payload
            )
            response.raise_for_status()
            return response.content
    except httpx.RequestError as e:
        raise PyWaBotConnectionError(f"Failed to download media: {e}") from e


async def send_reaction_to_server(
    context: SessionContext,
    jid: str,
    message_id: str,
    from_me: bool,
    emoji: str,
) -> Optional[Dict[str, Any]]:
    """Sends a reaction to a message for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "jid": jid,
            "messageId": message_id,
            "fromMe": from_me,
            "emoji": emoji,
        }
        return await _make_request(
            client, "post", f"{context.api_url}/send/reaction", json=payload
        )


async def update_group_participants(
    context: SessionContext,
    jid: str,
    action: str,
    participants: List[str],
) -> Optional[Dict[str, Any]]:
    """Updates participants in a group for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "jid": jid,
            "action": action,
            "participants": participants,
        }
        return await _make_request(
            client, "post", f"{context.api_url}/groups/{jid}/participants", json=payload
        )


async def send_link_preview_to_server(
    context: SessionContext,
    number: str,
    url: str,
    text: str,
) -> Optional[Dict[str, Any]]:
    """Sends a message with a link preview for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "number": number,
            "url": url,
            "text": text,
        }
        return await _make_request(
            client, "post", f"{context.api_url}/send/link-preview", json=payload
        )


async def send_media_to_server(
    context: SessionContext,
    number: str,
    message_payload: Dict[str, Any],
    timeout: int,
) -> Optional[Dict[str, Any]]:
    """Generic function to send media messages for a specific session."""
    async with _get_api_client(context.api_key, timeout=timeout) as client:
        payload = {
            "sessionName": context.session_name,
            "number": number,
            "message": message_payload,
        }
        return await _make_request(
            client, "post", f"{context.api_url}/send/message", json=payload
        )


async def pin_unpin_chat_on_server(
    context: SessionContext, jid: str, pin: bool
) -> bool:
    """Pins or unpins a chat for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {"sessionName": context.session_name, "jid": jid, "pin": pin}
        await _make_request(
            client, "post", f"{context.api_url}/chats/pin", json=payload
        )
        return True


async def create_group_on_server(
    context: SessionContext,
    title: str,
    participants: List[str],
) -> Optional[Dict[str, Any]]:
    """Creates a new group for a specific session."""
    async with _get_api_client(context.api_key) as client:
        payload = {
            "sessionName": context.session_name,
            "title": title,
            "participants": participants,
        }
        response = await _make_request(
            client, "post", f"{context.api_url}/groups/create", json=payload
        )
        return (
            response.get('data')
            if response and response.get('success')
            else None
        )


async def list_sessions(
    api_url: str, api_key: str
) -> Optional[Dict[str, Any]]:
    """Lists all available sessions on the server."""
    async with _get_api_client(api_key) as client:
        return await _make_request(client, "get", f"{api_url}/sessions/list")


async def delete_session(
    api_url: str, api_key: str, session_name: str
) -> bool:
    """Deletes a specific session from the server."""
    async with _get_api_client(api_key) as client:
        response = await _make_request(
            client, "delete", f"{api_url}/sessions/{session_name}/delete"
        )
        return response.get('success', False) if response else False
