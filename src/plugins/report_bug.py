import time
import re
from collections import deque
from typing import Any, Dict, List, Optional

from nonebot import get_driver, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, Message,MessageSegment
from nonebot.adapters import Bot as BaseBot
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor

# --- 配置 ---
EXCLUDE_COMMANDS = {"bug反馈", "报告bug"}
MAX_HISTORY = 30  # 适当增加历史容量以应对高频交互

def strip_emoji(text: str) -> str:
    emoji_pattern = re.compile(r"[\U00010000-\U0010FFFF]", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

recent_messages: Dict[str, deque] = {}

def _add_to_history(group_id: str, entry: dict):
    if group_id not in recent_messages:
        recent_messages[group_id] = deque(maxlen=MAX_HISTORY)
    entry["content"] = strip_emoji(entry["content"])
    recent_messages[group_id].append(entry)

# --- 1. 记录指令触发 (用户侧) ---
@run_postprocessor
async def record_actual_commands(matcher: Matcher, event: MessageEvent):
    raw_msg = str(event.message)
    if any(cmd in raw_msg for cmd in EXCLUDE_COMMANDS):
        return

    group_id = f"group_{event.group_id}" if isinstance(event, GroupMessageEvent) else f"private_{event.user_id}"
    _add_to_history(group_id, {
        "role": "user",
        "user_id": event.user_id,
        "group_id": event.group_id,
        "content": raw_msg,
        "time": time.time() # 使用浮点数记录更精确的时间
    })

# --- 2. 记录 Bot 发送 (Bot 侧) ---
@BaseBot.on_called_api
async def handle_api_result(bot: BaseBot, exception: Exception | None, api: str, data: Dict[str, Any], result: Any):
    if api in ["send_msg", "send_group_msg", "send_private_msg"] and exception is None:
        raw_output = data.get("message")
        content = str(Message(raw_output)) if raw_output else ""
        
        if "Bug反馈记录" in content or not content:
            return
            
        gid = data.get("group_id")
        uid = data.get("user_id")
        group_id = f"group_{gid}" if gid else f"private_{uid}"
        
        _add_to_history(group_id, {
            "role": "bot",
            "user_id": bot.self_id,
            "content": content,
            "time": time.time()
        })

# --- 3. 智能 Bug 反馈 ---
bug_report = on_command("bug反馈", aliases={"报告bug"}, priority=5, block=True)

@bug_report.handle()
async def report_bug(bot: Bot, event: MessageEvent):
    group_id = f"group_{event.group_id}" if isinstance(event, GroupMessageEvent) else f"private_{event.user_id}"
    history: List[dict] = list(recent_messages.get(group_id, []))
    
    current_user_id = event.user_id
    user_cmd: Optional[dict] = None
    bot_resp: Optional[dict] = None
    user_idx = -1

    # 1. 逆序查找该用户最后一次发送的非反馈指令
    for i in range(len(history) - 1, -1, -1):
        item = history[i]
        # 确保不抓到刚才发送的“bug反馈”本身（由于 postprocessor 还没运行，这里通常抓不到当前的反馈，但逻辑严谨起见）
        if item["role"] == "user" and item["user_id"] == current_user_id:
            if not any(cmd in item["content"] for cmd in EXCLUDE_COMMANDS):
                user_cmd = item
                user_idx = i
                break

    if user_cmd:
        # 2. 寻找与该指令时间最接近的 Bot 响应
        # 即使响应在指令前或后发生，只要时间差在 5 秒内就视为关联
        min_diff = 5.0 
        for j in range(len(history)):
            item = history[j]
            if item["role"] == "bot":
                diff = abs(item["time"] - user_cmd["time"])
                if diff < min_diff:
                    min_diff = diff
                    bot_resp = item

        # 格式化时间显示
        occur_time = time.strftime('%H:%M:%S', time.localtime(user_cmd['time']))
        report_header = (
            f"Bug反馈\n"
            f"时间戳: {int(time.time())})\n"
            f"反馈用户: {user_cmd['user_id']}\n"
            f"反馈群聊: {user_cmd['group_id']}\n"
            f"发生时间: {occur_time}\n"
            f"--------------------\n"
        )
        
        final_report = Message(report_header)
        final_report += Message("用户指令:\n") + Message(user_cmd['content'])
        
        bot_content = bot_resp['content'] if bot_resp else "(未捕获到对应响应，可能是静默执行或报错中断)"
        final_report += Message("\n\n机器人响应:\n") + Message(bot_content)

        await bot.send(event, "已静默抓取用户日志，正在上传至服务器以及发送给管理员...")
        await bot.send_msg(user_id=1097740481, message=final_report)
        await bug_report.finish(MessageSegment.reply(event.message_id)+"感谢你的反馈，已将该问题反馈给管理员。")
    else:
        await bot.send(event, "无法定位你刚才发送的指令，请确保你刚刚执行过其他功能。")