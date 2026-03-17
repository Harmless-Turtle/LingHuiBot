from pathlib import Path

from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
)
from nonebot.internal.matcher import Matcher

from ..commands import (
    wolf_kill_new,
    wolf_kill_join,
    wolf_kill_start,
    wolf_kill_over,
    wolf_kill_up_people,
    wolf_kill_down_people
)
from .check_rule import *
from src.plugins import utils

# 获取系统配置
config = get_driver().config
min_player = 8
max_player = 20
path = Path.cwd() / "data" / "wolfkill"

# 尝试导入自定义配置
try:
    min_player = config.lrs_min_player
    max_player = config.lrs_max_player
except AttributeError:
    logger.warning("未从dotEnv文件中获取到配置文件，将导入默认配置的人数上下限。")
    logger.warning(f"人数范围：{min_player}~{max_player}")

@wolf_kill_new.handle()
async def _wolf_kill_new(
        matcher: Matcher,
        event:GroupMessageEvent,
        room_file:Path = Depends(require_no_room),
):
    args = str(event.get_plaintext()).strip().split()
    # 解析自定义人数
    num_players = min_player
    if len(args) > 1:
        try:
            num_players = int(args[1])
            if num_players < min_player or num_players > max_player:
                await matcher.finish(
                    MessageSegment.reply(event.message_id) +
                    f"请输入{min_player}-{max_player}之间的玩家人数。"
                )
        except ValueError:
            await matcher.finish(
                MessageSegment.reply(event.message_id) +
                "请输入有效的玩家人数。"
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
        f"欢迎使用狼人杀小游戏awa\n已将您设置为本群的游戏房主。\n本局设置人数为{num_players}人，"
        f"未达到人数或未达到最低开始人数（{min_player}人）前无法开始游戏。\n通过“加入狼人杀”来加入游戏\n"
        f"通过“开始狼人杀”可以开始游戏。\n通过“删除狼人杀房间”可以删除当前房间。"
    )

@wolf_kill_join.handle()
async def _wolf_kill_join(
        matcher: Matcher,
        event:GroupMessageEvent,
        room_file:Path = Depends(require_room),
        _ = Depends(require_room)
):
    pass

@wolf_kill_start.handle()
async def _wolf_kill_start(
        matcher: Matcher,
        event: GroupMessageEvent,
):
    pass


@wolf_kill_over.handle()
async def _wolf_kill_over():
    pass

@wolf_kill_up_people.handle()
async def _wolf_kill_up_people():
    pass

@wolf_kill_down_people.handle()
async def _wolf_kill_down_people():
    pass