from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import Event, MessageEvent,GroupMessageEvent
from nonebot.message import event_preprocessor
from nonebot.exception import IgnoredException
from nonebot_plugin_orm import get_session

from .model import GroupBlacklist, UserBlacklist

# 获取超级用户列表
superusers = get_driver().config.superusers

@event_preprocessor
async def blacklist_processor(event: Event):
    # 如果不是消息事件（如心跳、撤回通知等），直接放行，不进入黑名单逻辑
    if not isinstance(event, MessageEvent):
        return
    # 提取用户和群聊的信息
    user_id = str(event.get_user_id())
    group_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else None
    # 排除超级用户
    if user_id in superusers:
        return
    # 建立数据库会话进行检查
    async with get_session() as session:
        # 检查用户黑名单
        user_check = await session.get(UserBlacklist, user_id)
        if user_check:
            logger.info(f"已拦截黑名单用户: {user_id}")
            raise IgnoredException("User in blacklist")
        # 检查群组黑名单
        if group_id:
            group_check = await session.get(GroupBlacklist, group_id)
            if group_check:
                logger.info(f"已拦截黑名单群组: {group_id}")
                raise IgnoredException("Group in blacklist")