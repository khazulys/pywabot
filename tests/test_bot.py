import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from pywabot.bot import PyWaBot
from pywabot.exceptions import ConnectionError
from pywabot.types import WaMessage

# --- Fixtures ---

@pytest.fixture
def mock_api_client(mocker):
    """Fixture to mock the entire api_client module."""
    return mocker.patch('pywabot.bot.api_client', autospec=True)

@pytest.fixture
def mock_websocket_client(mocker):
    """Fixture to mock the websocket_client module."""
    return mocker.patch('pywabot.bot.websocket_client', autospec=True)

@pytest.fixture
def mock_get_api_url(mocker):
    """Fixture to mock the _get_api_url function to return a predictable URL."""
    return mocker.patch('pywabot.bot._get_api_url', return_value="https://test.pywabot.com")

@pytest.fixture
def bot(mock_get_api_url):
    """Fixture to create a standard PyWaBot instance for tests."""
    # The mocked _get_api_url is automatically used here
    bot_instance = PyWaBot(session_name="test_session", api_key="test_api_key")
    return bot_instance

# --- Test Cases ---

def test_init_success(bot):
    """Test that PyWaBot initializes correctly with valid arguments."""
    assert bot.session_name == "test_session"
    assert bot.api_key == "test_api_key"
    assert bot.api_url == "https://test.pywabot.com"
    assert bot.websocket_url == "wss://test.pywabot.com"

def test_init_requires_session_name():
    """Test that PyWaBot raises ValueError if session_name is not provided."""
    with pytest.raises(ValueError, match="A session_name must be provided."):
        PyWaBot(session_name=None, api_key="some_key")

def test_init_requires_api_key():
    """Test that PyWaBot raises ValueError if api_key is not provided."""
    with pytest.raises(ValueError, match="An api_key must be provided."):
        PyWaBot(session_name="some_session", api_key=None)

@pytest.mark.asyncio
async def test_connect_success_when_uninitialized(bot, mock_api_client):
    """Test a successful connection flow when the server is not yet connected."""
    # Arrange
    mock_api_client.get_server_status.side_effect = ['uninitialized', 'connected']
    mock_api_client.start_server_session.return_value = (True, "Success")
    bot.wait_for_connection = AsyncMock(return_value=True)

    # Act
    connected = await bot.connect()

    # Assert
    assert connected is True
    bot.wait_for_connection.assert_called_once()
    mock_api_client.start_server_session.assert_called_once_with(
        "https://test.pywabot.com", "test_session"
    )

@pytest.mark.asyncio
async def test_connect_when_already_connected(bot, mock_api_client):
    """Test that connect() returns True immediately if already connected."""
    # Arrange
    mock_api_client.get_server_status.return_value = 'connected'

    # Act
    connected = await bot.connect()

    # Assert
    assert connected is True
    assert bot.is_connected is True
    mock_api_client.start_server_session.assert_not_called()

@pytest.mark.asyncio
async def test_send_message_when_connected(bot, mock_api_client):
    """Test sending a message when the bot is connected."""
    # Arrange
    bot.is_connected = True
    mock_api_client.send_message_to_server.return_value = {'success': True, 'data': 'message_data'}

    # Act
    result = await bot.send_message("123@s.whatsapp.net", "Hello")

    # Assert
    mock_api_client.send_message_to_server.assert_called_once_with(
        "https://test.pywabot.com", "123@s.whatsapp.net", "Hello", None, None
    )
    assert result == 'message_data'

@pytest.mark.asyncio
async def test_send_message_when_not_connected(bot):
    """Test that sending a message raises ConnectionError if not connected."""
    # Arrange
    bot.is_connected = False
    
    # Act & Assert
    with pytest.raises(ConnectionError, match="Bot is not connected."):
        await bot.send_message("123@s.whatsapp.net", "Hello")

@pytest.mark.asyncio
async def test_start_listening(bot, mock_websocket_client):
    """Test that start_listening calls the websocket client correctly."""
    # Arrange
    bot.is_connected = True
    
    # Act
    await bot.start_listening()

    # Assert
    mock_websocket_client.listen_for_messages.assert_called_once_with(
        bot.websocket_url,
        bot.api_key,
        bot.session_name,
        bot._process_incoming_message
    )

@pytest.mark.asyncio
async def test_command_handler_is_called(bot):
    """Test that a registered command handler is correctly called."""
    # Arrange
    mock_handler = AsyncMock()
    bot.handle_msg("/test")(mock_handler)
    
    test_message_data = {
        'messages': [{'key': {'remoteJid': '123@s.whatsapp.net', 'id': 'ABC'}, 'message': {'conversation': '/test command'}, 'pushName': 'Tester'}]
    }

    # Act
    await bot._process_incoming_message(test_message_data)
    
    # Assert
    mock_handler.assert_called_once()
    # Check that the handler was called with the correct types
    assert isinstance(mock_handler.call_args[0][0], PyWaBot)
    assert isinstance(mock_handler.call_args[0][1], WaMessage)
    assert mock_handler.call_args[0][1].text == '/test command'

@pytest.mark.asyncio
async def test_default_handler_is_called(bot):
    """Test that the default handler is called for non-command messages."""
    # Arrange
    mock_default_handler = AsyncMock()
    bot.on_message(mock_default_handler)
    
    test_message_data = {
        'messages': [{'key': {'remoteJid': '123@s.whatsapp.net', 'id': 'DEF'}, 'message': {'conversation': 'A normal message'}, 'pushName': 'Tester'}]
    }
    
    # Act
    await bot._process_incoming_message(test_message_data)
    
    # Assert
    mock_default_handler.assert_called_once()

@pytest.mark.asyncio
@patch('pywabot.bot.api_client.list_sessions', new_callable=AsyncMock)
@patch('pywabot.bot._get_api_url', return_value="https://static.test.com")
async def test_list_sessions(mock_get_url, mock_list):
    """Test the static list_sessions method."""
    # Arrange
    mock_list.return_value = ["session1", "session2"]

    # Act
    sessions = await PyWaBot.list_sessions(api_key="static_key")

    # Assert
    mock_list.assert_called_once_with("https://static.test.com")
    assert sessions == ["session1", "session2"]
