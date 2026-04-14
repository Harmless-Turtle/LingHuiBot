import random as rd
import asyncio
from typing import Dict, Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, Bot, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session

from src.plugins.entertainment.commands import guess_number
from src.plugins.utils import handle_errors
from src.plugins.entertainment.currency.models import get_user_coin, modify_user_coin

# 定义全局内存字典
active_games: Dict[int, Dict[str, Any]] = {}


@guess_number.handle()
@handle_errors
async def _(
        matcher: Matcher,
        bot: Bot,
        event: GroupMessageEvent,
        session: async_scoped_session,
):
    # 解析参数读取args值
    args = str(event.get_message()).split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        await matcher.finish(MessageSegment.reply(
            event.message_id) + "没有获取到正确的数据呢...请按照格式：\n猜数字 <猜的数字> <下注金额>来使用命令呢")

    user_guess_number, bet_amount = int(args[1]), int(args[2])
    group_id = event.group_id
    user_id = event.user_id

    # 检查余额
    mh_coin = await get_user_coin(session, str(user_id))
    if mh_coin < bet_amount:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你的墨辉币不足qwq...")

    # 扣除下注金额
    await modify_user_coin(session, str(user_id), -bet_amount)

    # 判断是否已开局
    is_first_player = group_id not in active_games

    # 当前下注数据
    new_bet = {"coin": bet_amount, "guess_number": user_guess_number}

    if is_first_player:
        # 初始化内存数据，player_data 里的每个用户对应一个下注列表
        active_games[group_id] = {
            "correct_number": rd.sample(range(1, 11), 2),
            "player_data": {
                user_id: [new_bet]
            }
        }
        await bot.send(event, f"这一局猜数字已经开始了捏uwu\n"
                              f"你对数字{user_guess_number}下注了{mh_coin}个墨辉币捏uwu\n"
                              f"将在60秒后进行结算。")
    else:
        # 如果该用户还没下注过，初始化列表；否则追加下注
        if user_id not in active_games[group_id]["player_data"]:
            active_games[group_id]["player_data"][user_id] = [new_bet]
        else:
            active_games[group_id]["player_data"][user_id].append(new_bet)
        await matcher.finish(MessageSegment.reply(event.message_id) + "下注成功，请等待开奖~")

    # 等待60s后继续
    await asyncio.sleep(60)

    # 结算
    game_data = active_games.pop(group_id, None)
    if not game_data:
        return

    correct_numbers = game_data["correct_number"]
    player_data = game_data["player_data"]

    winner_messages = []
    correct_count = 0

    # 遍历每个用户
    for uid, bets in player_data.items():
        user_win_total = 0
        # 遍历该用户的所有下注记录
        for bet in bets:
            if bet["guess_number"] in correct_numbers:
                user_win_total += bet["coin"] * 2

        # 如果该用户有中奖记录，统计并加钱
        if user_win_total > 0:
            correct_count += 1
            await modify_user_coin(session, str(uid), user_win_total)
            winner_messages.append(f"- {uid} 获得了 {user_win_total} 墨辉币")

    # 构建播报文本
    winner_str = "\n".join(winner_messages) if winner_messages else "没有人获奖呢qwq"
    group_correct_number_list = '、'.join([str(number) for number in correct_numbers])

    logger.info(f"群 {group_id} 猜数字开奖，正确数字: {group_correct_number_list}")

    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"正确数字是：{group_correct_number_list}\n"
        f"本场共有 {correct_count} 人猜对捏uwu！\n"
        f"{winner_str}"
    )