import random as rd
import time

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
    bank_money,
    bank_robbery
)
from src.plugins.utils import handle_errors,handle_json,at_is_true
from src.plugins.entertainment.check_files import bank_robbery_time_path


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
        await session.commit()
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

@bank_robbery.handle()
@handle_errors
async def _bank_robbery(
        matcher:Matcher,
        event:GroupMessageEvent,
        args:Message = CommandArg(),
        session:AsyncSession = Depends(get_session),
):
    # 获取at用户
    user_id = await at_is_true(event,args)
    # 执行初步数据合法性校验
    if user_id == "finish":
        await matcher.finish()
    elif not user_id.isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id)+"唔...似乎没有获取到你想要打劫的用户呢，请不要复制别人的at指令哦w")
    elif user_id == str(event.user_id):
        await matcher.finish(MessageSegment.reply(event.message_id) + "你不能打劫你自己哦！")
    # 生成随机数用来判断是否打劫银行成功
    correct = rd.randint(3, 3)
    # 获取当前时间
    now_time = int(time.time())
    # 获取计数器信息
    time_data = handle_json(bank_robbery_time_path,'r')
    # 尝试获取用户状态
    user_data = time_data.get(str(event.user_id),{})
    # 如果用户状态存在，则进入判断
    if user_data:
        # 确定过期时间：如果是 failure 则为 1 天，否则为 2 天
        duration = 86400 if user_data['robbery_mode'] == "failure" else 172800
        # 统一判断并删除
        if now_time - user_data['time'] >= duration:
            del time_data[str(event.user_id)]
        else:
            await matcher.finish(MessageSegment.reply(event.message_id)+f"你还在打劫别人银行的冷却时间内呢，不要这么贪心嘛qwq")
    # 匹配到失败的情况
    if correct != 3:
        time_data[f"{event.user_id}"] = {
            "time":int(time.time()),
            "robbery_mode":"failure"
        }
        result_text = "打劫失败了捏qwq\n你需要等待24小时后才可以继续抢劫别人的银行awa"
    # 否则匹配成功的情况。
    else:
        time_data[f"{event.user_id}"] = {
            "time":int(time.time()),
            "robbery_mode":"success"
        }
        # 获取被打劫银行用户的obj事务
        robbery_user_coin = int(await get_bank_coin(session=session, user_id=str(user_id)) * 0.1)
        if robbery_user_coin < 100:
            await matcher.finish(MessageSegment.reply(event.message_id)+"对方银行的墨辉币似乎都不够你打劫的awa")
        # 打劫成功，扣除用户的银行存款
        await bank_operation(
            session=session,
            user_id=str(user_id),
            amount=robbery_user_coin,
            operation="remove"
        )
        await bank_operation(
            session=session,
            user_id=str(event.user_id),
            amount=robbery_user_coin,
            operation="save"
        )
        await session.commit()
        self_coin = await get_bank_coin(session=session, user_id=str(event.user_id))
        result_text = f"打劫成功了捏uwu\n你劫走了对方银行的{robbery_user_coin}个墨辉币并存到了你自己的银行uwu\n你的银行现在还有{self_coin}个墨辉币捏~\n您需要等待48小时后才可以继续抢劫别人的银行awa"
    handle_json(bank_robbery_time_path,'w',time_data)
    await matcher.finish(MessageSegment.reply(event.message_id)+result_text)