"""
Test suite for the core functionality of the PyWaBot class.

This module contains a series of tests using pytest and unittest.mock to verify
the behavior of the PyWaBot, including initialization, connection logic,
message sending, and event handling. Fixtures are used to mock external
dependencies like the API and WebSocket clients, ensuring that tests are
isolated and repeatable.
"""
from unittest.mock import AsyncMock, patch

import pytest  # pylint: disable=import-error

from pywabot.bot import PyWaBot
from pywabot.exceptions import PyWaBotConnectionError  # pylint: disable=import-error
from pywabot.types import WaMessage


# --- Fixtures ---


@pytest.fixture
def mock_api_client_fixture(mocker):
    """Fixture to mock the entire api_client module."""
    return mocker.patch('pywabot.bot.api_client', autospec=True)


@pytest.fixture
def mock_websocket_client_fixture(mocker):
    """Fixture to mock the websocket_client module."""
    return mocker.patch('pywabot.bot.websocket_client', autospec=True)


@pytest.fixture
def mock_get_api_url_fixture(mocker):
    """Fixture to mock the _get_api_url function to return a predictable URL."""
    return mocker.patch(
        'pywabot.bot._get_api_url', return_value="https://test.pywabot.com"
    )


@pytest.fixture
def bot_instance_fixture(mock_get_api_url_fixture):  # pylint: disable=redefined-outer-name
    """
    Fixture to create a standard PyWaBot instance for tests.
    Note: The mocked _get_api_url is automatically used here.
    """
    # The unused `mock_get_api_url_fixture` is required to ensure the patch is active.
    _ = mock_get_api_url_fixture
    bot = PyWaBot(session_name="test_session", api_key="test_api_key")
    return bot


# --- Test Cases ---


def test_init_success(bot_instance_fixture):  # pylint: disable=redefined-outer-name
    """Test that PyWaBot initializes correctly with valid arguments."""
    assert bot_instance_fixture.session_name == "test_session"
    assert bot_instance_fixture.api_key == "test_api_key"
    assert bot_instance_fixture.api_url == "https://test.pywabot.com"
    assert bot_instance_fixture.websocket_url == "wss://test.pywabot.com"


def test_init_requires_session_name():
    """Test that PyWaBot raises ValueError if session_name is not provided."""
    with pytest.raises(ValueError, match="A session_name must be provided."):
        PyWaBot(session_name=None, api_key="some_key")


def test_init_requires_api_key():
    """Test that PyWaBot raises ValueError if api_key is not provided."""
    with pytest.raises(ValueError, match="An api_key must be provided."):
        PyWaBot(session_name="some_session", api_key=None)


@pytest.mark.asyncio
async def test_connect_success_when_uninitialized(bot_instance_fixture, mock_api_client_fixture):  # pylint: disable=redefined-outer-name
    """Test a successful connection flow when the server is not yet connected."""
    # Arrange
    mock_api_client_fixture.get_server_status.side_effect = ['uninitialized', 'connected']
    mock_api_client_fixture.start_server_session.return_value = (True, "Success")
    bot_instance_fixture.wait_for_connection = AsyncMock(return_value=True)

    # Act
    connected = await bot_instance_fixture.connect()

    # Assert
    assert connected is True
    bot_instance_fixture.wait_for_connection.assert_called_once()
    mock_api_client_fixture.start_server_session.assert_called_once_with(
        "https://test.pywabot.com", "test_session"
    )


@pytest.mark.asyncio
async def test_connect_when_already_connected(bot_instance_fixture, mock_api_client_fixture):  # pylint: disable=redefined-outer-name
    """Test that connect() returns True immediately if already connected."""
    # Arrange
    mock_api_client_fixture.get_server_status.return_value = 'connected'

    # Act
    connected = await bot_instance_fixture.connect()

    # Assert
    assert connected is True
    assert bot_instance_fixture.is_connected is True
    mock_api_client_fixture.start_server_session.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_when_connected(bot_instance_fixture, mock_api_client_fixture):  # pylint: disable=redefined-outer-name
    """Test sending a message when the bot is connected."""
    # Arrange
    bot_instance_fixture.is_connected = True
    mock_api_client_fixture.send_message_to_server.return_value = {
        'success': True,
        'data': 'message_data',
    }

    # Act
    result = await bot_instance_fixture.send_message("123@s.whatsapp.net", "Hello")

    # Assert
    mock_api_client_fixture.send_message_to_server.assert_called_once_with(
        "https://test.pywabot.com", "123@s.whatsapp.net", "Hello", None, None
    )
    assert result == 'message_data'


@pytest.mark.asyncio
async def test_send_message_when_not_connected(bot_instance_fixture):  # pylint: disable=redefined-outer-name
    """Test sending a message raises ConnectionError if not connected."""
    # Arrange
    bot_instance_fixture.is_connected = False

    # Act & Assert
    with pytest.raises(PyWaBotConnectionError, match="Bot is not connected."):
        await bot_instance_fixture.send_message("123@s.whatsapp.net", "Hello")


@pytest.mark.asyncio
async def test_start_listening(bot_instance_fixture, mock_websocket_client_fixture):  # pylint: disable=redefined-outer-name
    """Test that start_listening calls the websocket client correctly."""
    # Arrange
    bot_instance_fixture.is_connected = True

    # Act
    await bot_instance_fixture.start_listening()

    # Assert
    mock_websocket_client_fixture.listen_for_messages.assert_called_once_with(
        bot_instance_fixture.websocket_url,
        bot_instance_fixture.api_key,
        bot_instance_fixture.session_name,
        bot_instance_fixture._process_incoming_message,  # pylint: disable=protected-access
    )


@pytest.mark.asyncio
async def test_command_handler_is_called(bot_instance_fixture):  # pylint: disable=redefined-outer-name
    """Test that a registered command handler is correctly called."""
    # Arrange
    mock_handler = AsyncMock()
    bot_instance_fixture.handle_msg("/test")(mock_handler)

    test_message_data = {
        'messages': [
            {
                'key': {'remoteJid': '123@s.whatsapp.net', 'id': 'ABC'},
                'message': {'conversation': '/test command'},
                'pushName': 'Tester',
            }
        ]
    }

    # Act
    await bot_instance_fixture._process_incoming_message(  # pylint: disable=protected-access
        test_message_data
    )

    # Assert
    mock_handler.assert_called_once()
    # Check that the handler was called with the correct types
    assert isinstance(mock_handler.call_args[0][0], PyWaBot)
    assert isinstance(mock_handler.call_args[0][1], WaMessage)
    assert mock_handler.call_args[0][1].text == '/test command'


@pytest.mark.asyncio
async def test_default_handler_is_called(bot_instance_fixture):  # pylint: disable=redefined-outer-name
    """Test that the default handler is called for non-command messages."""
    # Arrange
    mock_default_handler = AsyncMock()
    bot_instance_fixture.on_message(mock_default_handler)

    test_message_data = {
        'messages': [
            {
                'key': {'remoteJid': '123@s.whatsapp.net', 'id': 'DEF'},
                'message': {'conversation': 'A normal message'},
                'pushName': 'Tester',
            }
        ]
    }

    # Act
    await bot_instance_fixture._process_incoming_message(  # pylint: disable=protected-access
        test_message_data
    )

    # Assert
    mock_default_handler.assert_called_once()


@pytest.mark.asyncio
@patch('pywabot.bot.api_client.list_sessions', new_callable=AsyncMock)
@patch('pywabot.bot._get_api_url', return_value="https://static.test.com")
async def test_list_sessions(mock_get_url, mock_list_sessions):
    """Test the static list_sessions method."""
    # Arrange
    _ = mock_get_url  # Unused but required for patching
    mock_list_sessions.return_value = ["session1", "session2"]

    # Act
    sessions = await PyWaBot.list_sessions(api_key="static_key")

    # Assert
    mock_list_sessions.assert_called_once_with("https://static.test.com")
    assert sessions == ["session1", "session2"]


@pytest.mark.asyncio
@patch('pywabot.bot.api_client.delete_session', new_callable=AsyncMock)
@patch('pywabot.bot._get_api_url', return_value="https://static.test.com")
async def test_delete_session(mock_get_url, mock_delete_session):
    """Test the static delete_session method."""
    # Arrange
    _ = mock_get_url  # Unused but required for patching
    mock_delete_session.return_value = (True, "Session deleted")

    # Act
    result, message = await PyWaBot.delete_session(
        session_name="session_to_delete", api_key="static_key"
    )

    # Assert
    mock_delete_session.assert_called_once_with(
        "https://static.test.com", "session_to_delete"
    )
    assert result is True
    assert message == "Session deleted"
