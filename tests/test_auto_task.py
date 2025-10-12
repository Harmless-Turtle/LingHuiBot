import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from src.plugins.birthday.tasks import _init_birthday_jobs


# Ensure NoneBot is initialized for plugin loading
try:
    nonebot.get_driver()
except ValueError:
    nonebot.init()

__import__("nonebot").require("nonebot_plugin_orm")
from nonebot.internal.matcher import Matcher
from nonebot.plugin import on_command


test_db = on_command("test_auto_task", priority=100, block=False)


@test_db.handle()
async def handle_test_db_func(matcher: Matcher):
    await matcher.send("Testing database...")
    await _init_birthday_jobs()


@pytest.mark.asyncio
@patch("src.plugins.birthday.tasks.get_bot")
@patch("src.plugins.birthday.tasks.get_session")
async def test_init_birthday_jobs(mock_get_session, mock_get_bot):
    # Arrange
    # Mocking the database result
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.tuples.return_value.all.return_value = [
        ("12345", "67890")
    ]
    mock_session.execute.return_value = mock_result
    mock_get_session.return_value.__aenter__.return_value = mock_session

    # Mocking the bot
    mock_bot = AsyncMock()
    mock_get_bot.return_value = mock_bot

    # Act
    await _init_birthday_jobs()

    # Assert
    # Verify that send_group_msg was called with the correct parameters
    mock_bot.send_group_msg.assert_called_once_with(
        group_id=67890,
        message=Message(MessageSegment.at(12345) + MessageSegment.text(" 生日快乐！")),
    )
