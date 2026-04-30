from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message, Bot
from nonebot.params import ArgPlainText, CommandArg
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import select

from .exceptions import CurrencyError, CurrencyInvalidAmount
from .models import get_mohui_data, add_mohui_coin, MoHuiCoinData
from ..commands import add_coin, check_coin, ranking_coin
from ...utils import handle_errors


@add_coin.handle()
@handle_errors
async def _add_coin(
        event: GroupMessageEvent,
        session: async_scoped_session,
        arg: str = ArgPlainText()
):
    try:
        if not arg.isdigit():
            raise CurrencyInvalidAmount("请输入一个正整数作为添加的墨辉币数量")
        amount = int(arg)
        balance = await add_mohui_coin(session, str(event.user_id), amount)

    except CurrencyError as e:
        await add_coin.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    await add_coin.finish(f"操作完成，添加了{amount}个墨辉币，当前墨辉币总额：{balance}")


@check_coin.handle()
@handle_errors
async def _check_coin(
        session: async_scoped_session,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    # 若消息后面存在文本则不响应
    if args.extract_plain_text():
        await check_coin.finish()

    coin_data = await get_mohui_data(session, str(event.user_id))
    await check_coin.finish(
        MessageSegment.reply(event.message_id) +
        f"您现在一共有{coin_data.mohui_coin}个墨辉币"
    )


@ranking_coin.handle()
@handle_errors
async def _ranking_coin(
        bot: Bot,
        session: async_scoped_session,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    # 若消息后面存在文本则不响应
    if args.extract_plain_text():
        await ranking_coin.finish()

    result = await session.execute(
        select(MoHuiCoinData.mohui_coin, MoHuiCoinData.user_id)
        .order_by(MoHuiCoinData.mohui_coin.desc(), MoHuiCoinData.user_id)
        .limit(10)
    )
    ranking = result.all()

    lines = []
    for idx, (mohui_coin, user_id) in enumerate(ranking, start=1):
        nickname = (
            (await bot.get_stranger_info(user_id=user_id))
            .get("nickname", str(user_id))
        )

        lines.append(f"{idx}. {nickname} - {mohui_coin} 个墨辉币")

    text = "\n".join(lines) or "暂无数据"

    await ranking_coin.finish(MessageSegment.reply(event.message_id) + text)
