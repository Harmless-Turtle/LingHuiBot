import re
from pathlib import Path
from types import SimpleNamespace

from nonebot import logger, on_request, on_notice
from nonebot.adapters.onebot.v11 import (
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
    PrivateMessageEvent,
    FriendRequestEvent,
    GroupMessageEvent,
    GroupRequestEvent,
    PokeNotifyEvent,
    NoticeEvent,
)
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command, on_type
from nonebot.rule import to_me, is_type, Rule

from ..utils import handle_json

path = Path.cwd() / 'data' / 'main'
welcome_path = path / "welcome_system.json"
check_group_member_path = path / "GroupMemberChange.json"
add_group_check_path = path / "add_group_switch.json"


async def check_bt(event: GroupMessageEvent):
    s = re.match(r'我是(.+)控', str(event.original_message))
    if s:
        return True
    else:
        return False


async def chek_add_welcome(event: GroupIncreaseNoticeEvent):
    welcome_data = handle_json(welcome_path, 'r')
    group_id = str(event.group_id)
    logger.info(f"检查群 {group_id} 的欢迎配置，当前数据：{welcome_data.get(group_id)}")
    if welcome_data.get(group_id, False):
        welcome_settings = welcome_data[group_id]
        logger.info(f"群 {group_id} 的欢迎模式为：{welcome_settings.get('mode')}")
        return welcome_settings.get('mode')
    return False


async def chek_group_member_change(event: GroupDecreaseNoticeEvent):
    try:
        data = handle_json(check_group_member_path, "r")
        logger.info(f"检查群 {event.group_id} 的退群通知开关，当前状态：{data.get(str(event.group_id))}")
        return data.get(str(event.group_id), False)
    except Exception as e:
        logger.error(f"读取退群通知配置失败：{e}")
        return False


async def add_group_switch(event: GroupRequestEvent):
    group_switch_data = handle_json(add_group_check_path, "r")
    logger.info(group_switch_data.get(str(event.group_id), False))
    logger.info(event.sub_type == "add")
    return group_switch_data.get(str(event.group_id), False) and event.sub_type == "add"


async def chek_friend_like(event: NoticeEvent):
    data = event.model_dump()
    data_sn = SimpleNamespace(**data)
    if getattr(data_sn, "sub_type", False):
        if data['sub_type'] == "profile_like":
            return True
        else:
            return False
    else:
        return False


async def chek_friend(event: PrivateMessageEvent):
    if event.message_type != "private":
        return False
    else:
        return True


##################
#     基础功能     #
##################
sign_in = on_command("签到", aliases={"好久不见"}, priority=2, block=True)
poke_check = on_type(PokeNotifyEvent, to_me())
tarot = on_command("塔罗牌", priority=4, block=True)
a_word = on_command("一言", priority=4, block=True)
btfrk = on_command("我是", rule=check_bt)
like = on_command("点赞", aliases={"赞我"}, block=True)
eat_what = on_command("今天吃什么")


#####################
#     入/退群检查     #
#####################
# 入群检查
# 加群请求同意
handle_group = on_command("允许加群", aliases={"拒绝加群"}, block=True)
# 入群检测开关监听器
add_group = on_request(rule=add_group_switch)
switch_add_group = on_command("入群检测", permission=SUPERUSER, block=True)
# 入群欢迎
change_welcome = on_command("入群欢迎", permission=SUPERUSER, block=True)
change_welcome_text = on_command("修改欢迎", aliases={"欢迎文本", "修改入群欢迎"}, permission=SUPERUSER, block=True)
# 是否提示退群
exit_change = on_command("退群提示", aliases={"退群提醒", "退群通知", "退群检测"}, block=True)
# 检查群成员减少事件
GroupExitMember = on_notice(
    rule=Rule(chek_group_member_change) & is_type(GroupDecreaseNoticeEvent),
    priority=1,
    block=True
)
#####################
#      其他功能       #
#####################
# 被点赞事件监测
like_friend = on_notice(rule=is_type(NoticeEvent) & chek_friend_like)
# 加好友事件请求
add_friend = on_request(rule=is_type(FriendRequestEvent), priority=1, block=True)
# 处理是否同意加好友
choice_friend = on_command("同意", rule=chek_friend, permission=SUPERUSER, aliases={"拒绝"}, block=True)
# 入群欢迎
add_welcome = on_notice(rule=is_type(GroupIncreaseNoticeEvent) & Rule(chek_add_welcome), priority=1, block=True)
# 自己被加进群的监听器
SelfJoinGroupWelcome = on_notice(rule=is_type(GroupIncreaseNoticeEvent), priority=1, block=True)
