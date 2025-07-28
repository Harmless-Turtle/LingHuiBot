from nonebot.matcher import Matcher
from ..Handler import Handler
import random as rd
from pathlib import Path
from nonebot.exception import ActionFailed
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Bot
)
import os
from nonebot import get_driver,logger


# 获取配置
config = get_driver().config
min_players = 5
max_players = 12
try:
    min_players = config.min_players_lrs
    max_players = config.max_players_lrs
except:
    logger.error("读取配置失败！将使用默认配置！")
    logger.info(f"默认最小玩家数: {min_players}, 最大玩家数: {max_players}")
    logger.warning("请在配置文件中设置min_players_lrs和max_players_lrs！")

path = Path.cwd() / 'data' / 'langrensha'

start = on_command("langrensha", aliases={"创建狼人杀","lrs"}, priority=5, block=True)
@start.handle()
async def _(matcher: Matcher, event: MessageEvent):
    args = str(event.get_plaintext()).strip().split()

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
    Handler.handle_json(room_file, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"欢迎使用狼人杀小游戏awa\n已将您设置为本群的游戏房主。\n本局设置人数为{num_players}人，未达到人数前无法开始游戏。\n通过“加入狼人杀”来加入游戏\n通过“开始狼人杀”可以开始游戏。\n通过“删除狼人杀房间”可以删除当前房间。")

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
    
    data = Handler.handle_json(room_file, 'r')
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
    Handler.handle_json(room_file, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"您已成功加入狼人杀游戏，当前玩家数：{len(data['players'])}/{data['max_players']}\n由于QQ限制，您必须添加凌辉Bot为好友后才能发起私聊会话，无法发起群聊临时会话。"
    )

# 编写开始游戏指令
start_game = on_command("开始狼人杀", aliases={"langrensha开始"}, priority=5, block=True)
@start_game.handle()
async def _(matcher: Matcher, event: MessageEvent,bot:Bot):
    room_file = path / f"{event.group_id}.json"
    if not room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "本群尚未创建狼人杀游戏房间，请先使用指令创建房间"
        )
    
    data = Handler.handle_json(room_file, 'r')
    if data['owner'] != event.user_id:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "只有房主才能开始游戏"
        )
    
    if len(data['players']) < min_players:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"当前玩家人数不足{min_players}人，无法开始游戏"
        )
    
    # 游戏开始逻辑
    data['status'] = 'playing'
    roles = ['狼人', '村民', '预言家', '女巫', '猎人']
    assigned_roles = rd.sample(roles * (len(data['players']) // len(roles) + 1), len(data['players']))
    
    for i, player in enumerate(data['players']):
        data['game_data'][player] = assigned_roles[i]
        await bot.send_private_msg(user_id=int(player),message=f"您的角色是：{data['game_data'][player]}。请注意保密！")
    Handler.handle_json(room_file, 'w', data)
        
    for player in data['players']:
        try:
            logger.info(player)
            
        except:
            os.remove(room_file)
            await matcher.finish(
                MessageSegment.reply(event.message_id) +
                f"致命错误：分配玩家 {player} 的身份时出现问题：发送私聊消息失败\n如未知原因，可添加凌辉Bot后再试。\n凌辉遇到了一个无法解决的错误，游戏已停止")
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        "游戏已开始！凌辉Bot已经私信告知了每位玩家所分配到的角色。请注意查收私信~"
    )

Delete_Room = on_command("删除狼人杀房间", aliases={"langrensha删除","dellrs"}, priority=5, block=True)
@Delete_Room.handle()
async def _(matcher: Matcher, event: MessageEvent):
    room_file = path / f"{event.group_id}.json"
    if not room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "本群尚未创建狼人杀游戏房间，请先使用指令创建房间"
        )
    
    data = Handler.handle_json(room_file, 'r')
    if data['owner'] != event.user_id:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "只有房主才能删除游戏房间"
        )
    
    os.remove(room_file)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        "狼人杀游戏房间已成功删除"
    )