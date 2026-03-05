import datetime
from typing import Annotated

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Depends
from nonebot.plugin.on import on_command, on_message
from nonebot.rule import is_type

from .models import (
    UserBirthday,
    GroupSettings,
    UserGroupUsage,
    get_or_create_user_birthday,
    delete_user_birthday as delete_user_birthday_dep,
    get_or_create_group_settings,
    inc_user_group_usage_today,
)
from .. import utils

toggle_birthday_feature = on_command("生日祝贺", priority=5, block=True)
set_birthday = on_command("我的生日是", priority=5, block=True)
delete_birthday = on_command("删除我的生日", priority=5, block=True)
birthday_greeting_responder = on_command("生日快乐", priority=5, block=True)
track_user_group_usage = on_message(is_type(GroupMessageEvent), priority=5, block=False)


@set_birthday.handle()
async def _set_birthday(
        matcher: Matcher,
        user_birthday: Annotated[UserBirthday, Depends(get_or_create_user_birthday)],
        args: Message = CommandArg()
):
    text = args.extract_plain_text().strip()
    try:
        parsed_birthday = datetime.datetime.strptime(text, "%m-%d")
        user_birthday.birthday_date = parsed_birthday.date()
        await matcher.send(f"你的生日已设置为 {parsed_birthday.strftime('%m-%d')}")
    except ValueError:
        await matcher.finish("请按格式发送，例如：/我的生日是 01-01")


@delete_birthday.handle()
async def _delete_birthday(matcher: Matcher, deleted: Annotated[bool, Depends(delete_user_birthday_dep)]):
    if not deleted:
        await matcher.send("你还没有设置生日呢。")
    else:
        await matcher.send("已删除你的生日信息。")


@toggle_birthday_feature.handle()
async def _toggle_birthday_feature(
        matcher: Matcher,
        group_settings: Annotated[GroupSettings, Depends(get_or_create_group_settings)]
):
    group_settings.enable = not group_settings.enable
    await matcher.send("已开启生日祝贺功能" if group_settings.enable else "已关闭生日祝贺功能")


@utils.handle_errors
@birthday_greeting_responder.handle()
async def _birthday_greeting_responder(
        matcher: Matcher,
        event: GroupMessageEvent,
        group_settings: Annotated[GroupSettings, Depends(get_or_create_group_settings)]
):
    group_msg = event.get_plaintext()
    if group_msg != "生日快乐" or not group_settings.enable:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    last_ts = group_settings.last_reply_ts
    if last_ts is not None and (now - last_ts) < datetime.timedelta(minutes=20):
        return

    await matcher.send("生日快乐")
    await matcher.send(
        '我可以记住所有人的生日，只要本人给我发"/我的生日是 mm-dd"就可以了~，到时候凌辉bot会找到你献上祝福语哦'
    )
    group_settings.last_reply_ts = now


@track_user_group_usage.handle()
async def _track_user_group_usage(_user_group_usage: Annotated[UserGroupUsage, Depends(inc_user_group_usage_today)]):
    pass
