from pathlib import Path
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.params import Depends
from src.plugins import utils  # 统一修改为和 wolfkill 相同的绝对导入以防报错

path = Path.cwd() / "data" / "entertainment" / "wolfkill"


# 1. 用于“新建房间”：如果房间已存在，则阻断
async def require_room_not_exists(event: GroupMessageEvent, matcher: Matcher) -> Path:
    room_file = path / f"{event.group_id}.json"
    if room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "本群已经存在狼人杀游戏房间，请使用其他指令进行操作")
    return room_file


# 2. 用于“已有房间操作”：如果房间不存在，则阻断
async def require_room_exists(event: GroupMessageEvent, matcher: Matcher) -> tuple[Path, dict]:
    room_file = path / f"{event.group_id}.json"
    if not room_file.exists():
        await matcher.finish(MessageSegment.reply(event.message_id) + "本群还未创建狼人杀房间，请先创建！")

    # 房间存在，读取数据并向下传递
    data = utils.handle_json(room_file, 'r')
    return room_file, data


# 3. 用于“加入等操作”：必须是等待状态（继承已有房间判断）
async def require_waiting(
        event: GroupMessageEvent,
        matcher: Matcher,
        room_data: tuple[Path, dict] = Depends(require_room_exists)
) -> tuple[Path, dict]:
    room_file, data = room_data
    if data['status'] != 'waiting':
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前群聊内的狼人杀房间已开始。")
    return room_data  # 继续向后传递数据


# 4. 用于“加入等操作”：必须未满员（继承等待状态判断）
async def require_not_full(
        event: GroupMessageEvent,
        matcher: Matcher,
        room_data: tuple[Path, dict] = Depends(require_waiting)
) -> tuple[Path, dict]:
    room_file, data = room_data
    if len(data['players']) >= data['max_players']:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"当前游戏已满员（{data['max_players']}人），无法加入")
    return room_data