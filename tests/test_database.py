import nonebot
from typing import Annotated

# Ensure NoneBot is initialized for plugin loading
try:
    nonebot.get_driver()
except ValueError:
    nonebot.init()

__import__("nonebot").require("nonebot_plugin_orm")
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.plugin import on_command

from plugins import GroupSettings, get_or_create_group_settings


test_db = on_command("test_db", priority=100, block=False)


@test_db.handle()
async def handle_test_db_func(matcher: Matcher,
                       group_settings: Annotated[GroupSettings, Depends(get_or_create_group_settings)]):
    await matcher.send("Testing database...")
    await matcher.send(f"group_settings.enable={group_settings.enable}")


import pytest
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.onebot.v11 import GroupMessageEvent

from plugins import GroupSettings, get_or_create_group_settings


# Helper to consume async generator
async def anext(async_generator):
    return await async_generator.__anext__()


@pytest.mark.asyncio
async def test_get_or_create_group_settings_new():
    # Arrange
    mock_session = AsyncMock()
    mock_session.get.return_value = None  # Simulate group not existing

    mock_event = MagicMock(spec=GroupMessageEvent)
    mock_event.group_id = 12345

    # Act
    settings_generator = get_or_create_group_settings(mock_session, mock_event)
    group_settings = await anext(settings_generator)

    # Assert
    mock_session.get.assert_called_once_with(GroupSettings, "12345")
    assert group_settings.group_id == "12345"
    assert not group_settings.enable

    # Test the finally block by trying to exhaust the generator
    with pytest.raises(StopAsyncIteration):
        await anext(settings_generator)

    mock_session.add.assert_called_once_with(group_settings)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_group_settings_existing():
    # Arrange
    existing_settings = GroupSettings(group_id="54321", enable=True)
    mock_session = AsyncMock()
    mock_session.get.return_value = existing_settings

    mock_event = MagicMock(spec=GroupMessageEvent)
    mock_event.group_id = 54321

    # Act
    settings_generator = get_or_create_group_settings(mock_session, mock_event)
    group_settings = await anext(settings_generator)

    # Assert
    mock_session.get.assert_called_once_with(GroupSettings, "54321")
    assert group_settings is existing_settings
    assert group_settings.enable

    # Test the finally block
    with pytest.raises(StopAsyncIteration):
        await anext(settings_generator)

    mock_session.add.assert_called_once_with(existing_settings)
    mock_session.commit.assert_called_once()
