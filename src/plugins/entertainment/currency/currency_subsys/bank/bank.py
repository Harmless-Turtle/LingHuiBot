import random as rd
import time

from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from .exceptions import BankError, InvalidTransferTarget
from .models import bank_operation, transfer_money, get_bank_data
from ....commands import (
    bank_transfer,
    bank_save,
    bank_remove,
    bank_money,
    bank_robbery
)
from .....entertainment.check_files import bank_robbery_time_path
from .....utils import handle_errors, handle_json


@bank_save.handle()
@handle_errors
async def bank_save(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    if not args.extract_plain_text().isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id) + "请输入正确的金额数字")
    amount = int(args.extract_plain_text())

    try:
        balance = await bank_operation(
            session=session,
            user_id=str(event.user_id),
            amount=amount,
            operation="save"
        )
        await session.commit()
    except BankError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"操作成功完成，存入银行{amount}个墨辉币，目前银行余额为{balance.bank_coin}个墨辉币"
    )


@bank_remove.handle()
@handle_errors
async def bank_remove(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    if not args.extract_plain_text().isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id) + "请输入正确的金额数字")
    amount = int(args.extract_plain_text())

    try:
        balance = await bank_operation(
            session=session,
            user_id=str(event.user_id),
            amount=amount,
            operation="remove"
        )
        await session.commit()
    except BankError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"操作成功完成，从银行取出了{amount}个墨辉币，目前银行余额为{balance.bank_coin}个墨辉币。"
    )


@bank_transfer.handle()
@handle_errors
async def bank_transfer(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    target_id: str | None = None
    amount = 0
    # 从消息中提取转账目标和金额
    for seg in args:
        if seg.type == "at":
            target_id = seg.data.get("qq")
        elif seg.type == "text":
            # 尝试提取文本中可能存在的数字
            text = seg.data["text"].strip()
            if text.isdigit():
                amount = int(text)

    try:
        await transfer_money(
            session=session,
            user_id=str(event.user_id),
            target_user_id=target_id,
            amount=amount
        )
        await session.commit()
    except BankError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    await matcher.finish(MessageSegment.reply(event.message_id) + "转账的操作成功了捏~")


@bank_money.handle()
@handle_errors
async def bank_money(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    if args.extract_plain_text(): await matcher.finish()
    bank_coin = await get_bank_data(session=session, user_id=str(event.user_id))
    await matcher.finish(MessageSegment.reply(event.message_id) + f"你的银行存款共有{bank_coin}个墨辉币捏uwu")


@bank_robbery.handle()
@handle_errors
async def _bank_robbery(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session
):
    # 获取at用户
    try:
        # 校验消息段长度，@后会自动跟空格所以可能是三段
        msg = event.original_message
        if not 2 <= len(msg) <= 3:
            raise BankError("参数格式错误！格式：抢劫@<一个用户>")

        # 校验是否是 at
        at_seg = msg[1]
        if not at_seg.type == "at":
            raise InvalidTransferTarget("唔...似乎没有获取到你想要打劫的用户呢，请不要复制别人的at指令哦w")

        target_id = str(at_seg.data.get("qq"))
        if target_id == str(event.user_id):
            raise InvalidTransferTarget("你不能打劫你自己哦！")

    except BankError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    # 生成随机数用来判断是否打劫银行成功
    correct = rd.randint(1, 10)
    # 获取当前时间
    now_time = int(time.time())
    # 获取计数器信息
    time_data = handle_json(bank_robbery_time_path, 'r')
    # 尝试获取用户状态
    user_data = time_data.get(str(event.user_id), {})
    # 如果用户状态存在，则进入判断
    if user_data:
        # 确定过期时间：如果是 failure 则为 1 天，否则为 2 天
        duration = 86400 if user_data['robbery_mode'] == "failure" else 172800
        # 统一判断并删除
        if now_time - user_data['time'] >= duration:
            del time_data[str(event.user_id)]
        else:
            if user_data['disturb']:
                time_data[str(event.user_id)]["disturb"] = False
                handle_json(bank_robbery_time_path, 'w', time_data)
                await matcher.finish(
                    MessageSegment.reply(event.message_id) +
                    f"你还在打劫别人银行的冷却时间内呢，不要这么贪心嘛qwq\n"
                    f"此消息仅会发送1次，直至时间足够刷新。"
                )
            await matcher.finish()
    # 匹配到失败的情况
    if correct != 3:
        time_data[f"{event.user_id}"] = {
            "time": int(time.time()),
            "robbery_mode": "failure",
            "disturb": True
        }
        result_text = "打劫失败了捏qwq\n你需要等待24小时后才可以继续抢劫别人的银行awa"
    # 否则匹配成功的情况。
    else:
        time_data[f"{event.user_id}"] = {
            "time": int(time.time()),
            "robbery_mode": "success",
            "disturb": True
        }
        # 获取被打劫银行用户的orm对象
        target_obj = await get_bank_data(session=session, user_id=str(target_id))
        robbery_user_coin = (target_obj.bank_coin * 0.1)
        if robbery_user_coin < 100:
            await matcher.finish(MessageSegment.reply(event.message_id) + "对方银行的墨辉币似乎都不够你打劫的awa")

        # 打劫成功，扣除用户的银行存款
        await transfer_money(
            session=session,
            user_id=str(target_id),
            target_user_id=str(event.user_id),
            amount=int(robbery_user_coin)
        )
        self_account = await get_bank_data(session=session, user_id=str(event.user_id))
        result_text = (
            f"打劫成功了捏uwu\n"
            f"你劫走了对方银行的{robbery_user_coin}个墨辉币并存到了你自己的银行uwu\n"
            f"你的银行现在还有{self_account.bank_coin}个墨辉币捏~\n"
            f"您需要等待48小时后才可以继续抢劫别人的银行awa"
        )
    handle_json(bank_robbery_time_path, 'w', time_data)
    await matcher.finish(MessageSegment.reply(event.message_id) + result_text)
