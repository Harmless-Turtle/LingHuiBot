import random as rd
from pathlib import Path

from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from .models import (
    add_drift_bottle,
    get_or_create_drift_bottle_group_config,
    get_random_drift_bottle,
)
from ..commands import add_battle, auto_switch_battle, pick_battle
from ...Exceptions import UserVisibleError
from ...utils import handle_errors, handle_json


@add_battle.handle()
@handle_errors
async def _add_battle(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    arg: Message = CommandArg(),
):
    text = arg.extract_plain_text().strip()
    if not text:
        raise UserVisibleError("唔...参数解析失败了，请检查是否按照“扔漂流瓶<这里输入你想说的话>”的格式使用呢")
    if len(text) >= 150:
        raise UserVisibleError("唔...你输入的内容太长了哦，请限制在150字以内呢xwx")

    await add_drift_bottle(session, event, text)
    await session.commit()

    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + "你的漂流瓶已经投进了大海...\n让我们猜一下它会飘向何处吧~"
    )


@pick_battle.handle()
@handle_errors
async def _pick_battle(
    matcher: Matcher,
    bot: Bot,
    event: MessageEvent,
    session: async_scoped_session,
):
    bottle = await get_random_drift_bottle(session)
    # 数据库没有内容的 fallback 分支
    if bottle is None:
        word_list = handle_json(Path.cwd() / "data" / "main" / "aword.json", "r")
        result = rd.choice(word_list)
        await matcher.finish(
            MessageSegment.reply(event.message_id)
            + f"大海里一眼望不到头，但就是没有看到漂流瓶呢awa\n但是~凌辉有一句一言哦w~\n“{result}”"
        )

    # 提前解构 ORM 属性，杜绝 commit 后读取引发 MissingGreenlet
    bottle_user_id = int(bottle.user_id)
    bottle_content = str(bottle.data)
    await session.commit()

    stranger_info = await bot.get_stranger_info(user_id=bottle_user_id)
    nickname = stranger_info.get("nickname", "来自远方的旅人")

    await matcher.finish(
        MessageSegment.reply(event.message_id)
        + f"在遥远的大海中飘来了一个小小的瓶子，它的里面写着：{bottle_content}\n"
        f"署名是：“{nickname}”\n"
        "Tip：如果您发现了违规的漂流瓶内容，请发送“bug反馈”将本次使用记录反馈给管理员。管理员会酌情对违规用户进行处罚\n"
        "十分感谢您的配合。"
    )


@auto_switch_battle.handle()
@handle_errors
async def _auto_switch_battle(
    matcher: Matcher,
    event: GroupMessageEvent,
    session: async_scoped_session,
    args: Message = CommandArg(),
):
    # 若消息后面存在文本则不响应
    if args.extract_plain_text():
        await matcher.finish()

    # 检查权限
    user_role = event.sender.role
    superusers = get_driver().config.superusers
    if str(event.user_id) not in superusers and user_role == "member":
        raise UserVisibleError("唔...你不是凌辉su用户或者群管理员，没办法操控这个开关呢xwx")

    config = await get_or_create_drift_bottle_group_config(session, str(event.group_id))
    config.enable = not config.enable
    mode = config.enable
    await session.commit()

    text = "已开启随机漂流功能，漂流瓶会在随机的时间里被送到本群呢w" if mode else "已关闭随机漂流功能"
    await matcher.finish(MessageSegment.reply(event.message_id) + f"{text}")
