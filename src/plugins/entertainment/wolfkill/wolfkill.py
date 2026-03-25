from nonebot.adapters.onebot.v11 import Message
from nonebot import on_command
wolf_kill_help = on_command("狼人杀帮助", aliases={"狼人杀说明", "狼人杀指南"})
# 狼人杀帮助指令
@wolf_kill_help.handle()
async def _wolf_kill_help(matcher: Matcher):
    guide_path = Path(__file__).parent / "wolfkill_guide.md"
    if guide_path.exists():
        with open(guide_path, encoding="utf-8") as f:
            content = f.read()
        await matcher.finish(Message(content))
    else:
        await matcher.finish("未找到狼人杀用户指南。")
# 自动判定胜负指令
from nonebot import on_command
wolf_kill_auto_check = on_command("自动判定胜负")

@wolf_kill_auto_check.handle()
async def _wolf_kill_auto_check(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_room_exists),
):
    room_file, data = room_data
    from .wolfkill_game import WolfKillGame
    game = WolfKillGame(room_file, data)
    winner = game.auto_check_and_finish()
    if winner == '狼人':
        await matcher.finish("狼人阵营胜利！游戏结束。")
    elif winner == '好人':
        await matcher.finish("好人阵营胜利！游戏结束。")
    else:
        await matcher.finish("游戏尚未结束，无胜负。")
from pathlib import Path

from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageSegment,
)
from nonebot.internal.matcher import Matcher
from nonebot.params import Depends

from ..commands import (
    wolf_kill_new,
    wolf_kill_join,
    wolf_kill_start,
    wolf_kill_over,
    wolf_kill_up_people,
    wolf_kill_down_people,
    wolf_kill_vote,
    wolf_kill_tally,
    wolf_kill_check_win
)

# 白天投票指令
@wolf_kill_vote.handle()
async def _wolf_kill_vote(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_room_exists),
):
    room_file, data = room_data
    from .wolfkill_game import WolfKillGame
    game = WolfKillGame(room_file, data)
    args = str(event.get_plaintext()).strip().split()
    if len(args) < 2:
        await matcher.finish("请指定你要投票的玩家ID，如：投票狼人杀 123456")
    try:
        target_id = int(args[1])
    except ValueError:
        await matcher.finish("请输入有效的玩家ID")
    game.cast_vote(event.user_id, target_id)
    await matcher.finish(f"你已投票给玩家{target_id}")

# 票数结算指令
@wolf_kill_tally.handle()
async def _wolf_kill_tally(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_room_exists),
):
    room_file, data = room_data
    from .wolfkill_game import WolfKillGame
    game = WolfKillGame(room_file, data)
    out = game.tally_vote()
    if out is None:
        await matcher.finish("平票，没有玩家被淘汰。")
    else:
        await matcher.finish(f"玩家{out}被淘汰出局！")

# 胜负判定指令
@wolf_kill_check_win.handle()
async def _wolf_kill_check_win(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_room_exists),
):
    room_file, data = room_data
    from .wolfkill_game import WolfKillGame
    game = WolfKillGame(room_file, data)
    winner = game.check_win()
    if winner == '狼人':
        await matcher.finish("狼人阵营胜利！")
    elif winner == '好人':
        await matcher.finish("好人阵营胜利！")
    else:
        await matcher.finish("游戏尚未结束。")
from .check_rule import require_room_not_exists, require_room_exists, require_waiting, require_not_full
from .wolfkill_game import WolfKillGame
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
        event: GroupMessageEvent,
        room_file: Path = Depends(require_room_not_exists),
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
        f"因为客户端暂不支持发起群临时会话，要正常发起私聊，请先添加机器人好友。"
    )


@wolf_kill_join.handle()
async def _wolf_kill_join(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_not_full),
):
    room_file, data = room_data
    if event.user_id in data['players']:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你已经在游戏房间里了，不可以重复进入呢")

    data['players'].append(event.user_id)
    utils.handle_json(room_file, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"加入成功！当前人数：{len(data['players'])}/{data['max_players']}")


@wolf_kill_start.handle()
async def _wolf_kill_start(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_waiting),
):
    room_file, data = room_data
    if event.user_id != data['owner']:
        await matcher.finish(MessageSegment.reply(event.message_id) + "只有房主才能开始游戏！")

    if len(data['players']) < min_player:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"当前人数不足，最低需要 {min_player} 人。")

    # 分配角色
    game = WolfKillGame(room_file, data)
    role_map = game.assign_roles()
    data['status'] = 'gaming'
    game.save()
    # 通知房主分配结果（实际应私聊通知每位玩家自己的身份，这里仅示例）
    msg = "游戏开始！已分配角色。\n"
    for pid, role in role_map.items():
        msg += f"玩家{pid}: {role}\n"
    await matcher.finish(MessageSegment.reply(event.message_id) + msg)


@wolf_kill_over.handle()
async def _wolf_kill_over(
        matcher: Matcher,
        event: GroupMessageEvent,
        room_data: tuple[Path, dict] = Depends(require_room_exists),
):
    room_file, data = room_data
    if event.user_id != data['owner']:
        await matcher.finish(MessageSegment.reply(event.message_id) + "只有房主才能解散房间！")

    room_file.unlink(missing_ok=True)
    await matcher.finish(MessageSegment.reply(event.message_id) + "游戏房间已解散！")


@wolf_kill_up_people.handle()
async def _wolf_kill_up_people():
    pass


@wolf_kill_down_people.handle()
async def _wolf_kill_down_people():
    pass