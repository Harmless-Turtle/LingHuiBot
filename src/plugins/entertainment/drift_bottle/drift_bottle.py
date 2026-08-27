import random as rd
from pathlib import Path

from nonebot import get_driver
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Message, Bot, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from .exceptions import DriftBottleError
from .models import (
    add_drift_bottle,
    get_random_drift_bottle,
    get_or_create_drift_bottle_group_config,
)
from ..commands import add_battle, pick_battle, auto_switch_battle
from ...utils import handle_json


@add_battle.handle()
async def _add_battle(event: GroupMessageEvent, session: async_scoped_session, arg: Message = CommandArg()):
    try:
        # 解析
        text = arg.extract_plain_text().strip()
        if text == "":
            raise DriftBottleError("唔...参数解析失败了，请检查是否按照“扔漂流瓶<这里输入你想说的话>”的格式使用呢")
        if len(text) >= 150:
            raise DriftBottleError("唔...你输入的内容太长了哦，请限制在150字以内呢xwx")

        # 落库
        await add_drift_bottle(session, event, text)
        await session.commit()

    except DriftBottleError as e:
        await add_battle.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    await add_battle.finish(
        MessageSegment.reply(event.message_id) +
        "你的漂流瓶已经投进了大海...\n"
        "让我们猜一下它会飘向何处吧~"
    )


@pick_battle.handle()
async def _pick_battle(bot: Bot, event: MessageEvent, session: async_scoped_session):
    try:
        bottle = await get_random_drift_bottle(session)
        # 数据库没有内容的 fallback 分支
        if bottle is None:
            word_list = handle_json(
                Path.cwd() / 'data' / 'main' / "aword.json",
                'r'
            )
            result = rd.choice(word_list)

            await pick_battle.finish(
                MessageSegment.reply(event.message_id) +
                f"大海里一眼望不到头，但就是没有看到漂流瓶呢awa\n"
                f"但是~凌辉有一句一言哦w~\n"
                f"“{result}”"
            )
            return

        await session.commit()
        stranger_info = await bot.get_stranger_info(user_id=int(bottle.user_id))
        nickname = stranger_info.get('nickname', '来自远方的旅人')

        await pick_battle.finish(
            MessageSegment.reply(event.message_id) +
            f"在遥远的大海中飘来了一个小小的瓶子，它的里面写着：{bottle.data}\n"
            f"署名是：“{nickname}”\n"
            f"Tip：如果您发现了违规的漂流瓶内容，请发送“bug反馈”将本次使用记录反馈给管理员。管理员会酌情对违规用户进行处罚\n"
            f"十分感谢您的配合。"
        )

    except DriftBottleError as e:
        await pick_battle.finish(MessageSegment.reply(event.message_id) + e.message)


@auto_switch_battle.handle()
async def _auto_switch_battle(
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg(),
):
    # 若消息后面存在文本则不响应
    if args.extract_plain_text():
        await auto_switch_battle.finish()
        return

    # 检查权限
    user_role = event.sender.role
    superusers = get_driver().config.superusers
    if str(event.user_id) not in superusers and user_role == "member":
        await auto_switch_battle.finish(
            MessageSegment.reply(event.message_id) +
            "唔...你不是凌辉su用户或者群管理员，没办法操控这个开关呢xwx"
        )

    try:
        config = await get_or_create_drift_bottle_group_config(session, str(event.group_id))
        mode = not config.enable

        await session.commit()
    except DriftBottleError as e:
        await auto_switch_battle.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    text = "已开启随机漂流功能，漂流瓶会在随机的时间里被送到本群呢w" if mode else "已关闭随机漂流功能"
    await auto_switch_battle.finish(MessageSegment.reply(event.message_id) + f"{text}")
