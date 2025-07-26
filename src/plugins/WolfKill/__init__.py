from .langrensha import (
    start,
    join,
    start_game,
    Delete_Room,
)

__plugin_name__ = "狼人杀游戏"
__plugin_usage__ = """
创建狼人杀<人数>    -创建一个<人数>人狼人杀房间，在群内进行游戏
加入狼人杀    -加入当前群内的狼人杀游戏房间
开始狼人杀    -开始当前群内的狼人杀游戏
删除狼人杀房间 -删除当前群内的狼人杀游戏房间
创建房间时人数范围为5~12人，默认5人。游戏开始后，玩家可以通过私聊Bot进行操作。
狼人杀游戏需要玩家添加Bot为好友以便进行私聊操作。
"""

# 导出处理器以便NoneBot自动加载
__all__ = [
    start,
    join,
    start_game,
    Delete_Room,
]