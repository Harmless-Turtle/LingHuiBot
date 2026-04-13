import random as rd
import asyncio

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, Bot, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session

from src.plugins.entertainment.commands import guess_number
from src.plugins.entertainment.check_files import guess_number_path
from src.plugins.utils import handle_errors
from src.plugins.entertainment.currency.models import MoHuiCoinData,get_user_coin,modify_user_coin
from .tools import add_bet, get_user_bet_amount


@guess_number.handle()
@handle_errors
async def _(
       matcher: Matcher,
        bot: Bot,
        event: GroupMessageEvent,
        session: async_scoped_session,
):
    # 获取用户输入数据
    args = str(event.get_message()).split()
    # 判断数据合法性
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        await matcher.finish(MessageSegment.reply(event.message_id)+"没有获取到正确的数据呢...请按照格式：\n猜数字 <猜的数字> <下注金额>来使用命令呢")
    # 获取猜的数字和下注金额
    user_guess_number,bet_amount = int(args[1]),int(args[2])
    # 获取用户余额
    MHCoin = get_user_coin(session, str(event.user_id))
    if MHCoin < bet_amount:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你的墨辉币不够你进行这一次猜数字的qwq...")
    
    logger.info(f"用户 {event.user_id} 在群 {event.group_id} 发送了猜数字指令，参数：{args}")
    # 生成三个唯一数字（范围1~10）
    numbers = rd.sample(range(1, 11), 2)
