__import__("nonebot").require("nonebot_plugin_orm")
__import__("nonebot").require("nonebot_plugin_apscheduler")
import datetime
from pathlib import Path
from typing import Annotated

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot.plugin.on import on_command, on_message
from nonebot.rule import startswith, is_type
from nonebot_plugin_orm import async_scoped_session

from src.database.models.birthday_orm import GroupSettings, UserGroupUsage, get_or_create_group_settings, \
    inc_user_group_usage_today
from src.plugins import utils

HAPPY_BIRTHDAY_OPTIONS_PATH = Path() / 'data' / 'happy_birthday_options.json'

happy_birthday_option = on_command("生日祝贺", priority=5, block=True)
happy_birthday_behavior = on_message(rule=startswith("生日快乐", False), priority=5, block=True)
user_group_usage = on_message(is_type(GroupMessageEvent), priority=5, block=False)


@utils.handle_errors
@happy_birthday_option.handle()
async def happy_birthday(matcher: Matcher, session: async_scoped_session,
                         event: GroupMessageEvent,
                         group_settings: Annotated[GroupSettings, Depends(get_or_create_group_settings)],
                         ):
    group_settings.enable = True if not group_settings.enable else False
    await session.commit()

    await matcher.finish("已开启生日祝贺功能" if group_settings.enable else "已关闭生日祝贺功能")


@utils.handle_errors
@happy_birthday_behavior.handle()
async def happy_birthday_behavior(matcher: Matcher,
                                  event: GroupMessageEvent,
                                  session: async_scoped_session,
                                  hb_options: Annotated[GroupSettings, Depends(get_or_create_group_settings)],
                                  ):
    group_msg = event.get_message()
    if group_msg != "生日快乐" or not hb_options.enable:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    last_ts = hb_options.last_reply_ts
    if last_ts is not None and (now - last_ts) < datetime.timedelta(minutes=20):
        return

    await matcher.send("生日快乐")
    hb_options.last_reply_ts = now
    await session.commit()


@utils.handle_errors
@user_group_usage.handle()
async def user_group_usage_handler(_event: GroupMessageEvent, _session: async_scoped_session,
                                   _user_group_usage: Annotated[UserGroupUsage, Depends(inc_user_group_usage_today)]):
    # 仅用于触发 Depends(inc_user_group_usage_today) 执行每日群用量统计
    pass
