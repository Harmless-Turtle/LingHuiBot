from nonebot.matcher import Matcher
from src.plugins import utils
import random as rd
from pathlib import Path
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent
)



path = Path.cwd() / 'data' / 'langrensha'

start = on_command("langrensha", aliases={"创建狼人杀"}, priority=5, block=True)


@start.handle()
async def _(matcher: Matcher, event: MessageEvent):
    args = str(event.get_plaintext()).strip().split()
    min_players = 5  # 狼人杀最少人数
    max_players = 12  # 可自定义最大人数

    # 解析自定义人数
    num_players = min_players
    if len(args) > 1:
        try:
            num_players = int(args[1])
            if num_players < min_players or num_players > max_players:
                await matcher.finish(
                    MessageSegment.reply(event.message_id) +
                    f"请输入{min_players}-{max_players}之间的玩家人数。"
                )
        except ValueError:
            await matcher.finish(
                MessageSegment.reply(event.message_id) +
                "请输入有效的玩家人数。"
            )

    if not event.group_id:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "请在群聊中使用狼人杀小游戏"
        )
    room_file = path / f"{event.group_id}.json"
    if room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "本群已经存在狼人杀游戏房间，请使用其他指令进行操作"
        )
    data = {
        "owner": event.user_id,
        "players": [event.user_id],
        "status": "waiting",
        "game_data": {},
        "max_players": num_players
    }
    utils.handle_json(room_file, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"欢迎使用狼人杀小游戏awa\n已将您设置为本群的游戏房主。\n本局设置人数为{num_players}人，未达到人数前无法开始游戏。")


# 编写群员加入指令
join = on_command("加入狼人杀", aliases={"langrensha加入"}, priority=4, block=True)


@join.handle()
async def _(matcher: Matcher, event: MessageEvent):
    room_file = path / f"{event.group_id}.json"
    if not room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "本群尚未创建狼人杀游戏房间，请先使用指令“创建狼人杀 <这里输入人数，支持5~12人游玩，默认5人>”创建房间"
        )

    data = utils.handle_json(room_file, 'r')
    if data['status'] != 'waiting':
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "当前游戏已开始，无法加入新玩家"
        )

    if event.user_id in data['players']:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "您已经在游戏中"
        )

    if len(data['players']) >= data['max_players']:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"当前游戏已满员（{data['max_players']}人），无法加入"
        )

    data['players'].append(event.user_id)
    utils.handle_json(room_file, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"您已成功加入狼人杀游戏，当前玩家数：{len(data['players'])}/{data['max_players']}"
    )


# 编写开始游戏指令
start_game = on_command("开始狼人杀", aliases={"langrensha开始"}, priority=5, block=True)


@start_game.handle()
async def _(matcher: Matcher, event: MessageEvent):
    room_file = path / f"{event.group_id}.json"
    if not room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "本群尚未创建狼人杀游戏房间，请先使用指令创建房间"
        )

    data = utils.handle_json(room_file, 'r')
    if data['owner'] != event.user_id:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "只有房主才能开始游戏"
        )

    if len(data['players']) < 5:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "当前玩家人数不足5人，无法开始游戏"
        )

    # 游戏开始逻辑
    data['status'] = 'playing'
    roles = ['狼人', '村民', '预言家', '女巫', '猎人']
    assigned_roles = rd.sample(roles * (len(data['players']) // len(roles) + 1), len(data['players']))

    for i, player in enumerate(data['players']):
        data['game_data'][player] = assigned_roles[i]

    utils.handle_json(room_file, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        "游戏已开始！各位玩家请查看自己的角色"
    )
