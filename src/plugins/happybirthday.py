import time
from pathlib import Path

from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.plugin.on import on_command, on_message
from nonebot.rule import startswith

from src.plugins import utils

HAPPY_BIRTHDAY_OPTIONS_PATH = Path() / 'data' / 'happy_birthday_options.json'

# 记录每个群上一次发送“生日快乐”的时间戳（单位：秒）
_last_birthday_reply_ts: dict[int, float] = {}

happy_birthday_option = on_command("打开生日祝贺", priority=5, block=True)
happy_birthday_behavior = on_message(rule=startswith("生日快乐", False), priority=5, block=True)


@utils.handle_errors
@happy_birthday_option.handle()
async def happy_birthday(matcher: Matcher, event: GroupMessageEvent):
    # 若配置文件不存在，则创建并为当前群写入开启状态
    if not HAPPY_BIRTHDAY_OPTIONS_PATH.exists():
        HAPPY_BIRTHDAY_OPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        # 修正：以群号为键写入 True
        utils.handle_json(HAPPY_BIRTHDAY_OPTIONS_PATH, "w", {str(event.group_id): True})

        await matcher.finish("已开启生日祝贺功能")
        return

    # 文件存在则读取并判断状态（兼容整型与字符串键）
    read_options = utils.handle_json(HAPPY_BIRTHDAY_OPTIONS_PATH, 'r') or {}
    gid = int(event.group_id)
    result = read_options.get(str(gid))
    if result is None:
        result = read_options.get(gid)

    if result is None or result is False:
        await matcher.finish("已关闭生日祝贺功能")
    else:
        await matcher.finish("已开启生日祝贺功能")


@utils.handle_errors
@happy_birthday_behavior.handle()  # 修正：注册处理器
async def happy_birthday_behavior(matcher: Matcher, event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text != "生日快乐":
        return

    # 读取该群功能开关，未开启则不响应
    read_options = utils.handle_json(HAPPY_BIRTHDAY_OPTIONS_PATH, 'r') or {}
    enabled = read_options.get(str(event.group_id))
    if enabled is None:
        enabled = read_options.get(event.group_id)
    if not enabled:
        return

    now = time.time()
    last_ts = _last_birthday_reply_ts.get(event.group_id, 0.0)
    # 20 分钟内不重复发送
    if now - last_ts < 20 * 60:
        return

    await matcher.send("生日快乐")
    _last_birthday_reply_ts[event.group_id] = now
