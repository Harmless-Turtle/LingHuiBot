from nonebot.adapters.onebot.v11 import GroupMessageEvent,Message
from nonebot_plugin_orm import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from .items import *

async def initialization_fishing_user(
        session: AsyncSession,
        event: GroupMessageEvent):
    pass