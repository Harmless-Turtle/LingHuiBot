from pathlib import Path
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.params import Depends
from plugins import utils

path = Path.cwd() / "data" / "wolfkill"


# 若房间不存在，则直接拒绝请求
async def require_no_room(event: GroupMessageEvent, matcher: Matcher) -> dict:
    room_file = path / f"{event.group_id}.json"
    if not room_file.exists():
        await matcher.finish(MessageSegment.reply(event.message_id) + "本群还未创建狼人杀房间，请先创建！")
    return utils.handle_json(room_file, 'r')



# 若房间已存在，则传递到已开始判断和满员判断等已有房间的操作
async def require_room(event: GroupMessageEvent, matcher: Matcher):
    room_file = path / f"{event.group_id}.json"
    if room_file.exists():
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "本群已经存在狼人杀游戏房间，请使用其他指令进行操作")
    return room_file

async def require_waiting(event: GroupMessageEvent, matcher: Matcher, data: dict = Depends(require_room)):
    if data['status'] != 'waiting':
        await matcher.finish(MessageSegment.reply(event.message_id) + "当前群聊内的狼人杀房间已开始。")
    return data  # 继续向后传递数据

async def require_not_full(event: GroupMessageEvent, matcher: Matcher, data: dict = Depends(require_room)):
    if len(data['players']) >= data['max_players']:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"当前游戏已满员（{data['max_players']}人），无法加入")