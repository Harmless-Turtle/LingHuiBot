from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg,Depends
from nonebot_plugin_orm import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from .models import bank_operation, transfer_money,get_bank_coin
from src.plugins.entertainment.commands import (
    bank_transfer,
    bank_save,
    bank_remove,
    bank_money
)
from src.plugins.utils import handle_errors



@bank_save.handle()
@handle_errors
async def bank_save(
        matcher:Matcher,
        event:GroupMessageEvent,
        args:Message = CommandArg(),
        session: AsyncSession = Depends(get_session),
):
    if not args.extract_plain_text().isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id)+"请输入正确的金额数字")
    amount = int(args.extract_plain_text())
    async with session.begin():
        text = await bank_operation(
            session=session,
            user_id=str(event.user_id),
            amount=amount,
            operation="save")
    await matcher.finish(MessageSegment.reply(event.message_id)+text)

@bank_remove.handle()
@handle_errors
async def bank_remove(
        matcher:Matcher,
        event:GroupMessageEvent,
        args:Message = CommandArg(),
        session: AsyncSession = Depends(get_session),
):
    if not args.extract_plain_text().isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id)+"请输入正确的金额数字")
    amount = int(args.extract_plain_text())
    async with session.begin():
        text = await bank_operation(
            session=session,
            user_id=str(event.user_id),
            amount=amount,
            operation="remove")
    await matcher.finish(MessageSegment.reply(event.message_id)+text)

@bank_transfer.handle()
@handle_errors
async def bank_transfer(
        matcher:Matcher,
        event:GroupMessageEvent,
        args:Message = CommandArg(),
        session: AsyncSession = Depends(get_session),
):
    target_id = None
    amount = 0
    for seg in args:
        if seg.type == "at":
            target_id = seg.data.get("qq")
        elif seg.type == "text":
            # 尝试提取文本中可能存在的数字
            text = seg.data["text"].strip()
            if text.isdigit():
                amount = int(text)
    # 校验数据完整性
    if not target_id:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请在命令后艾特想要转账的用户哦~")
    if amount <= 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "请正确输入转账金额，例如：转账 @用户 100")
    async with session.begin():
        text = await transfer_money(
            session=session,
            user_id=str(event.user_id),
            to_user_id=str(target_id),
            amount=amount
        )
    await matcher.finish(MessageSegment.reply(event.message_id)+text)

@bank_money.handle()
@handle_errors
async def bank_money(
        matcher:Matcher,
        event:GroupMessageEvent,
        args:Message = CommandArg(),
        session: AsyncSession = Depends(get_session),
):
    if args.extract_plain_text(): await matcher.finish()
    bank_coin = await get_bank_coin(session=session, user_id=str(event.user_id))
    await matcher.finish(MessageSegment.reply(event.message_id)+f"你的银行存款共有{bank_coin}个墨辉币捏uwu")