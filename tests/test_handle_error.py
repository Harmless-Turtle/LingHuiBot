import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.matcher import Matcher

from src.plugins.utils import handle_errors


# A simple async function that raises an exception, to be decorated
async def original_function_that_raises_exception(matcher: Matcher, event: MessageEvent):
    raise Exception("This is a test exception.")


@pytest.mark.asyncio
@patch("src.plugins.utils.generate_text_image")
async def test_handle_errors_decorator(mock_generate_text_image):
    # Arrange
    mock_matcher = AsyncMock(spec=Matcher)
    mock_matcher.finish = AsyncMock()

    mock_event = MagicMock(spec=MessageEvent)
    mock_event.message_id = 12345

    # Mock the image generation to avoid file system operations
    mock_image = MagicMock()
    mock_generate_text_image.return_value = mock_image

    # Act
    # Decorate the function manually for testing
    decorated_function = handle_errors(original_function_that_raises_exception)
    await decorated_function(matcher=mock_matcher, event=mock_event)

    # Assert
    # Check if matcher.finish was called, indicating the error was handled
    mock_matcher.finish.assert_called_once()

    # You can also add more specific assertions, for example,
    # checking the content of the message passed to finish.
    # This requires more complex mocking of MessageSegment and other parts.
