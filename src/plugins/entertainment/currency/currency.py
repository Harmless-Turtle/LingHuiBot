from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment,Message

from src.plugins.utils import handle_errors
from ..commands import (
    add_coin,
    check_coin,
)
from .models import (
    get_user_coin,
    modify_user_coin,
)



@add_coin.handle()
@handle_errors
async def _add_coin(
    matcher: Matcher,
    event: GroupMessageEvent, session: async_scoped_session
):
    raw_info = str(event.raw_message).split(" ")
    operate_coins = int(raw_info[1])
    new_balance = await modify_user_coin(session, str(event.user_id), operate_coins)
    await matcher.finish(f"操作完成，添加了{operate_coins}个墨辉币，当前墨辉币总额：{new_balance}")


@check_coin.handle()
@handle_errors
async def _check_coin(
        matcher:Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent,
        args:Message = CommandArg()
):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    balance = await get_user_coin(session, str(event.user_id))
    await matcher.finish(MessageSegment.reply(event.message_id)+f"您现在一共有{balance}个墨辉币")

