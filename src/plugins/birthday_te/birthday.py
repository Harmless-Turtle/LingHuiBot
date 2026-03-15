from typing import Annotated
import datetime

from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent,Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Depends
from nonebot_plugin_orm import async_scoped_session

from .commands import *
from .models import (
    GroupSettings,
    get_group_settings,
    UserBirthdayData,
    delete_user_birthday
)




@birthday_switch.handle()
async def _toggle_birthday_feature(
        matcher: Matcher,
        group_settings: Annotated[GroupSettings,Depends(get_group_settings)],
        event: MessageEvent,
):
    group_settings.enable = not group_settings.enable
    text = "已开启生日祝贺功能" if group_settings.enable else "已关闭生日祝贺功能"
    await matcher.finish(MessageSegment.reply(event.message_id)+text)

@birthday_add.handle()
async def _birthday_add(
        matcher: Matcher,
        session:async_scoped_session,
        event: MessageEvent,
        args:Message = CommandArg()
):
    group_id = event.group_id
    group_obj = await session.get(GroupSettings, group_id)
    user_id = event.user_id
    user_obj = await session.get(UserBirthdayData, user_id)
    text = args.extract_plain_text().strip()
    text_len = len(text.strip("-"))
    if text_len < 2:
        await matcher.finish(MessageSegment.reply(event.message_id)+"唔...格式不正确，请按格式发送。例如：我的生日是 01-01或2008-01-01")
    date_format = "%Y-%m-%d"
    if text_len == 2:
        date_format = "%m-%d"
    try:
        parsed_birthday = datetime.datetime.strptime(text, date_format)
        user_obj.birthday_date = parsed_birthday.date()
        group_enable_text = ""
        if not group_obj.enable:
            group_enable_text = "（思考）唔...这个群似乎还没有打开全局生日祝贺，只有在联系群管理组打开全局生日祝贺之后这个功能才会生效呢TAT...\n（发送”生日祝贺“四个字就可以打开啦~）\n"
        await matcher.send(MessageSegment.reply(event.message_id)+f"{group_enable_text}你的生日已设置为 {parsed_birthday.strftime(date_format)}")
    except ValueError:
        await matcher.finish(MessageSegment.reply(event.message_id)+"请按格式发送，例如：我的生日是 01-01 或者 我的生日是 2008-01-01\n请注意：只接受空格间隔，无间隔或换行都将驳回请求。")

@birthday_del.handle()
async def _delete_birthday(matcher: Matcher, deleted: Annotated[bool, Depends(delete_user_birthday)]):
    if not deleted:
        await matcher.send("你还没有设置生日呢。")
    else:
        await matcher.send("已删除你的生日信息。")