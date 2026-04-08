from nonebot.internal.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

from src.plugins.utils import handle_errors
from ..commands import (
    add_coin,
    check_coin,
    del_coin_sys
)
from .models import (
    get_user_coin,
    modify_user_coin,
)



@add_coin.handle()
@handle_errors
async def _add_coin(
    event: GroupMessageEvent, session: async_scoped_session
):
    raw_info = str(event.raw_message).split(" ")
    operate_coins = int(raw_info[1])
    new_balance = await modify_user_coin(session, str(event.user_id), operate_coins)
    await add_coin.finish(f"操作完成，添加了{operate_coins}个墨辉币，当前墨辉币总额：{new_balance}")


@check_coin.handle()
@handle_errors
async def _check_coin(
        matcher:Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent
):
    balance = await get_user_coin(session, str(event.user_id))
    await matcher.finish(MessageSegment.reply(event.message_id)+f"您现在一共有{balance}个墨辉币")

@del_coin_sys.handle()
@handle_errors
async def _delete_user_coin_record():
    pass