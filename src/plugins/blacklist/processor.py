from typing import Literal
from nonebot import get_driver, logger, on_notice
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import Event, GroupBanNoticeEvent
from pathlib import Path
from nonebot.rule import Rule

from src.plugins import utils

path = Path.cwd() / 'data'
black_list_path = path / "blacklist" / "black_list.json"


# 初始化检查
def init_blacklist():
    """确保黑名单文件存在且格式正确"""
    utils.ensure_files_exist([black_list_path], "黑名单插件",[{}])
    data = utils.handle_json(black_list_path, 'r')
    # 如果文件是空的列表或格式不对，初始化为字典
    if not isinstance(data, dict):
        data = {"user": [], "group": []}
        utils.handle_json(black_list_path, 'w', data)
    return data


init_blacklist()


# --- 工具函数 ---

def add_to_blacklist(target_id: str, type_: Literal['user', 'group']) -> bool:
    """
    将 ID 加入特定类别的黑名单
    :param target_id: 用户 QQ 或群号
    :param type_: 'user' 或 'group'
    """
    black_list = utils.handle_json(black_list_path, 'r')

    # 确保字典键存在
    if type_ not in black_list:
        black_list[type_] = []

    if target_id not in black_list[type_]:
        black_list[type_].append(target_id)
        utils.handle_json(black_list_path, 'w', black_list)
        return True
    return False


# --- 自动化功能：机器人被禁言自动拉黑群 ---


async def check_ban(event: GroupBanNoticeEvent) -> bool:
    # duration > 0 是禁言，duration == 0 是解除禁言
    return event.is_tome() and event.duration > 0


auto_ban = on_notice(
    rule=Rule(check_ban),
    priority=1,
    block=False
)


# --- 预处理器 ---

@event_preprocessor
def black_processor(event: Event):
    uid = vars(event).get('user_id')
    gid = vars(event).get('group_id')

    uid_str = str(uid) if uid else None
    gid_str = str(gid) if gid else None

    # 1. 管理员白名单放行
    superusers = get_driver().config.superusers
    if uid_str in superusers:
        return

    # 2. 读取黑名单字典
    black_list = utils.handle_json(black_list_path, 'r')
    if not isinstance(black_list, dict):
        return

    # 3. 分类检索拦截
    # 检查用户黑名单
    if uid_str and uid_str in black_list.get('user', []):
        logger.debug(f"用户 {uid_str} 在黑名单中，忽略请求")
        raise IgnoredException("黑名单用户")

    # 检查群组黑名单
    if gid_str and gid_str in black_list.get('group', []):
        logger.debug(f"群聊 {gid_str} 已被设为静默状态")
        raise IgnoredException("黑名单群组")
