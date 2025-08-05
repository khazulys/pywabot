from dataclasses import dataclass
from typing import Optional


class WaMessage:
    def __init__(self, raw_message):
        self.raw = raw_message
        self._msg_info = raw_message.get('messages', [{}])[0] if raw_message.get('messages') else {}
        
        self.key = self._msg_info.get('key', {})
        self.id = self.key.get('id')
        self.chat = self.key.get('remoteJid')
        self.from_me = self.key.get('fromMe', False)
        self.sender = self.key.get('participant') or self.chat
        
        self.sender_name = self._msg_info.get('pushName') or "Unknown"
        self.timestamp = self._msg_info.get('messageTimestamp')

        self.message = self._msg_info.get('message') or {}
        self.text = self.message.get('conversation') or \
                    self.message.get('extendedTextMessage', {}).get('text') or \
                    (self.message.get('ephemeralMessage', {}).get('message') or {}).get('extendedTextMessage', {}).get('text')

        self.location = self.message.get('locationMessage')
        self.document = self.message.get('documentMessage')
        self.image = self.message.get('imageMessage')
        self.video = self.message.get('videoMessage')
        self.audio = self.message.get('audioMessage')

    def get_location(self):
        if self.location:
            return {
                'latitude': self.location.get('degreesLatitude'),
                'longitude': self.location.get('degreesLongitude')
            }
        return None


class WaGroupMetadata:
    def __init__(self, metadata):
        self.id = metadata.get('id')
        self.owner = metadata.get('owner')
        self.subject = metadata.get('subject')
        self.creation = metadata.get('creation')
        self.desc = metadata.get('desc')
        self.participants = metadata.get('participants', [])

    def __str__(self):
        return f"Group: {self.subject} ({self.id})"


class PollMessage:
    def __init__(self, data):
        self.id = data.get('id')
        self.chat = data.get('chat')
        self.sender = data.get('sender')
        self.name = data.get('name')
        self.options = data.get('options', [])
        self.selectable_options_count = data.get('selectableOptionsCount')

    def __str__(self):
        return f"Poll: {self.name} with options: {self.options}"


class LinkPreview:
    def __init__(self, data):
        self.id = data.get('id')
        self.chat = data.get('chat')
        self.sender = data.get('sender')
        self.text = data.get('text')
        self.url = data.get('url')
        self.title = data.get('title')
        self.description = data.get('description')
        self.thumbnail_url = data.get('thumbnailUrl')

    def __str__(self):
        return f"Link Preview: {self.title} ({self.url})"


@dataclass
class Gif:
    url: str
    caption: Optional[str] = None


@dataclass
class Image:
    url: str
    caption: Optional[str] = None


@dataclass
class Audio:
    url: str
    mimetype: str = 'audio/mpeg'


@dataclass
class Video:
    url: str
    caption: Optional[str] = None
