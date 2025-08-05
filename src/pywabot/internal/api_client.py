import httpx
import logging
import json
import os
from ..exceptions import APIError, ConnectionError, AuthenticationError, APIKeyMissingError

logger = logging.getLogger(__name__)

def _get_api_client(**kwargs):
    api_key = os.environ.get("PYWABOT_API_KEY")
    if not api_key:
        raise APIKeyMissingError(
            "API Key not found. Please set the PYWABOT_API_KEY environment variable."
        )
    headers = {"X-API-Key": api_key}
    return httpx.AsyncClient(headers=headers, **kwargs)

async def _make_request(client, method, url, **kwargs):
    try:
        logger.debug(f"Making API request: {method.upper()} {url}")
        if 'json' in kwargs:
            logger.debug(f"Request payload: {json.dumps(kwargs['json'], indent=2)}")

        response = await client.request(method, url, **kwargs)
        
        logger.debug(f"Received API response: Status {response.status_code}")

        response.raise_for_status()

        if response.status_code == 204:
            logger.debug("Response has no content.")
            return None

        logger.debug(f"Raw response text: {response.text}")
        return response.json()
    except httpx.HTTPStatusError as e:
        response_data = {}
        error_message = e.response.text
        if e.response.content:
            try:
                response_data = e.response.json()
                error_message = response_data.get('message', e.response.text)
            except json.JSONDecodeError:
                pass
        
        logger.error(f"API request failed: Status {e.response.status_code} - {error_message}")

        if e.response.status_code in [401, 403]:
            raise AuthenticationError(error_message, status_code=e.response.status_code)
        raise APIError(error_message, status_code=e.response.status_code)
    except httpx.RequestError as e:
        raise ConnectionError(f"Failed to connect to the API: {e}")

async def start_server_session(api_url, session_name):
    async with _get_api_client() as client:
        try:
            payload = {"sessionName": session_name}
            await _make_request(client, "post", f"{api_url}/start-session", json=payload)
            return True, "Session initialized successfully."
        except APIError as e:
            if e.status_code == 400 and "already active" in e.message:
                return True, "A session is already active."
            raise
        except ConnectionError as e:
            return False, str(e)

async def get_server_status(api_url):
    try:
        async with _get_api_client() as client:
            data = await _make_request(client, "get", f"{api_url}/status")
            return data.get('status')
    except (ConnectionError, APIKeyMissingError):
        return 'server_offline'

async def request_pairing_code(api_url, phone_number, session_name):
    async with _get_api_client(timeout=120.0) as client:
        payload = {"number": phone_number, "sessionName": session_name}
        data = await _make_request(client, "post", f"{api_url}/pair-code", json=payload)
        return data.get('code')

async def send_message_to_server(api_url, number, message, reply_chat=None, mentions=None):
    async with _get_api_client(timeout=30.0) as client:
        payload = {"number": number, "message": message}
        if reply_chat and 'messages' in reply_chat.raw and reply_chat.raw['messages']:
            payload["quotedMessage"] = reply_chat.raw['messages'][0]
        if mentions:
            payload["mentions"] = mentions
        return await _make_request(client, "post", f"{api_url}/send-message", json=payload)

async def update_presence_on_server(api_url, jid, state):
    async with _get_api_client() as client:
        payload = {"jid": jid, "state": state}
        await _make_request(client, "post", f"{api_url}/presence-update", json=payload)
        return True

async def get_group_metadata(api_url, jid):
    async with _get_api_client() as client:
        return await _make_request(client, "get", f"{api_url}/group-metadata/{jid}")

async def forward_message_to_server(api_url, jid, message_obj):
    async with _get_api_client() as client:
        payload = {"jid": jid, "message": message_obj}
        await _make_request(client, "post", f"{api_url}/forward-message", json=payload)
        return True

async def edit_message_on_server(api_url, jid, message_id, new_text):
    async with _get_api_client() as client:
        payload = {"jid": jid, "messageId": message_id, "newText": new_text}
        await _make_request(client, "post", f"{api_url}/edit-message", json=payload)
        return True

async def update_chat_on_server(api_url, jid, action, message=None):
    async with _get_api_client() as client:
        payload = {"jid": jid, "action": action}
        if message:
            payload["message"] = message
        await _make_request(client, "post", f"{api_url}/chat/update", json=payload)
        return True

async def send_poll_to_server(api_url, number, name, values):
    async with _get_api_client() as client:
        payload = {"number": number, "name": name, "values": values}
        return await _make_request(client, "post", f"{api_url}/send-poll", json=payload)

async def download_media_from_server(api_url, message):
    try:
        async with _get_api_client() as client:
            payload = {"message": message}
            response = await client.post(f"{api_url}/download-media", json=payload)
            response.raise_for_status()
            return response.content
    except httpx.RequestError as e:
        raise ConnectionError(f"Failed to download media: {e}")

async def send_reaction_to_server(api_url, jid, message_id, from_me, emoji):
    async with _get_api_client() as client:
        payload = {
            "jid": jid,
            "messageId": message_id,
            "fromMe": from_me,
            "emoji": emoji
        }
        return await _make_request(client, "post", f"{api_url}/send-reaction", json=payload)

async def update_group_participants(api_url, jid, action, participants):
    async with _get_api_client() as client:
        payload = {
            "jid": jid,
            "action": action,
            "participants": participants
        }
        return await _make_request(client, "post", f"{api_url}/group-participants-update", json=payload)

async def send_link_preview_to_server(api_url, number, url, text):
    async with _get_api_client() as client:
        payload = {"number": number, "url": url, "text": text}
        return await _make_request(client, "post", f"{api_url}/send-link-preview", json=payload)


async def send_gif_to_server(api_url, number, gif):
    async with _get_api_client(timeout=30.0) as client:
        payload = {
            "number": number,
            "message": {
                "video": {"url": gif.url},
                "caption": gif.caption,
                "gifPlayback": True
            }
        }
        return await _make_request(client, "post", f"{api_url}/send-message", json=payload)


async def send_image_to_server(api_url, number, image):
    async with _get_api_client(timeout=30.0) as client:
        payload = {
            "number": number,
            "message": {
                "image": {"url": image.url},
                "caption": image.caption
            }
        }
        return await _make_request(client, "post", f"{api_url}/send-message", json=payload)


async def send_audio_to_server(api_url, number, audio):
    async with _get_api_client(timeout=30.0) as client:
        payload = {
            "number": number,
            "message": {
                "audio": {"url": audio.url},
                "mimetype": audio.mimetype
            }
        }
        return await _make_request(client, "post", f"{api_url}/send-message", json=payload)


async def send_video_to_server(api_url, number, video):
    async with _get_api_client(timeout=60.0) as client:
        payload = {
            "number": number,
            "message": {
                "video": {"url": video.url},
                "caption": video.caption
            }
        }
        return await _make_request(client, "post", f"{api_url}/send-message", json=payload)


async def pin_unpin_chat_on_server(api_url, jid, pin):
    async with _get_api_client() as client:
        payload = {"jid": jid, "pin": pin}
        await _make_request(client, "post", f"{api_url}/chat/pin", json=payload)
        return True


async def create_group_on_server(api_url, title, participants):
    async with _get_api_client() as client:
        payload = {"title": title, "participants": participants}
        response = await _make_request(client, "post", f"{api_url}/group-create", json=payload)
        return response.get('data') if response and response.get('success') else None

async def list_sessions(api_url):
    async with _get_api_client() as client:
        response = await _make_request(client, "get", f"{api_url}/sessions")
        return response.get('sessions', [])

async def delete_session(api_url, session_name):
    async with _get_api_client() as client:
        response = await _make_request(client, "delete", f"{api_url}/sessions/{session_name}")
        return response.get('success', False)
