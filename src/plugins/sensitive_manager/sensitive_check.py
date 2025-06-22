import json
import os
import datetime
from pathlib import Path
from typing import Dict, Set, List, Optional
import ahocorasick
from nonebot import get_driver, on_command, on_message
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    GroupMessageEvent,
    Bot,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import Rule
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.exception import MatcherException
import sys
sys.path.append("/home/LingHui/NoneBot/LingHuiBot/src")
from plugins.Handler import Handler

# 配置文件路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "sensitive_manager"
SENSITIVE_DATA_PATH = DATA_DIR / "sensitive_data.json"
GROUP_SETTINGS_PATH = DATA_DIR / "group_settings.json"
USER_VIOLATIONS_PATH = DATA_DIR / "user_violations.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

driver = get_driver()
sensitive_admins = json.loads(os.getenv("SENSITIVEADMIN",[1097740481,1692719245]))
logger.info(f"敏感词管理员列表: {sensitive_admins}")

class SensitiveManager:
    def __init__(self):
        self.ac_dict: Dict[str, ahocorasick.Automaton] = {}
        self.sensitive_words: Dict[str, Set[str]] = {}  # 确保数据结构正确
        self.load_data()
        
        # 初始化时遍历所有群组构建 AC 自动机
        self.build_all_ac()  # 新增方法

        self.group_settings = Handler.load_json(GROUP_SETTINGS_PATH,'r')
        self.user_violations = Handler.load_json(USER_VIOLATIONS_PATH,'r')

    def load_data(self):
        """加载敏感词数据（兼容旧格式）"""
        data = Handler.load_json(SENSITIVE_DATA_PATH, 'r')
        self.sensitive_words = {}
        for group_id, content in data.items():
            # 旧数据兼容：content为列表时转为新结构
            if isinstance(content, list):
                self.sensitive_words[group_id] = {
                    "words": set(content),
                    "admin": []
                }
            else:
                self.sensitive_words[group_id] = {
                    "words": set(content.get("words", [])),
                    "admin": content.get("admin", [])
                }
    def build_all_ac(self):
        """初始化时构建所有群组的 AC 自动机"""
        for group_id in self.sensitive_words:
            self.build_ac(group_id)

    def build_ac(self, group_id: str):
        """为指定群组构建 AC 自动机"""
        group_data = self.sensitive_words.get(group_id, {})
        words = group_data.get("words", set())  # 正确获取"words"字段的集合
        ac = ahocorasick.Automaton()
        for word in words:
            ac.add_word(word, word)
        ac.make_automaton()
        self.ac_dict[group_id] = ac
        

    def get_group_words(self, group_id: str) -> Set[str]:
        return self.sensitive_words.get(group_id, {}).get("words", set())
    
    def is_admin(self, user_id: str) -> bool:
        return user_id in sensitive_admins

manager = SensitiveManager()

async def check_enabled(event: GroupMessageEvent) -> bool:
    group_id = str(event.group_id)
    return manager.group_settings.get(group_id, False)

sensitive_matcher = on_message(
    rule=Rule(check_enabled),
    priority=10,
    block=False
)

@sensitive_matcher.handle()
async def handle_check(matcher:Matcher,bot: Bot, event: GroupMessageEvent):
    text = event.get_plaintext()
    user_id = str(event.user_id)
    group_id = str(event.group_id)

    # 获取当前群的AC自动机进行检测
    ac = manager.ac_dict.get(group_id)
    found_words = set()
    if ac:
        for _, word in ac.iter(text):
            found_words.add(word)

    if not found_words:
        return

    # 更新违规记录
    violations = manager.user_violations.get(user_id, {
        "count": 0,
        "warnings": 0,
        "records": []
    })
    if found_words:
        # 获取管理员列表并发送通知
        group_info = manager.sensitive_words.get(group_id, {})
        admins = group_info.get("admin", [])
        for admin_id in admins:
            try:
                await bot.send_private_msg(
                    user_id=int(admin_id),
                    message=f"群{group_id}有用户触发敏感词:\n用户：{event.user_id}\n内容：{text}\n触发词汇：{','.join(found_words)}\n用户已违规次数：{violations["count"]}"
                )
            except Exception as e:
                logger.error(f"通知管理员失败：{e}")
    from datetime import datetime as dt
    timestamp = event.time  # 获取整数时间戳（秒级）
    dt_object = dt.fromtimestamp(timestamp)  # 转换为 datetime 对象
    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间

    violations["count"] += 1
    violations["records"].append({
        "time": formatted_time,
        "group": group_id,
        "content": text
    })

    # 处理惩罚逻辑
    action_taken = False
    if violations["count"] % 3 == 0:
        violations["warnings"] += 1
        warn_level = violations["warnings"]
        Role = await bot.get_group_member_info(group_id=event.group_id,user_id=event.self_id)
        Role = Role['role']
        if Role not in "member":
            if warn_level == 1:
                await bot.set_group_ban(group_id=group_id, user_id=event.user_id, duration=7*24*60*60)
                action_taken = True
                await matcher.finish(MessageSegment.reply(event.message_id)+f"检测到敏感词，并且已经累计3次违规，禁言7天")
            elif warn_level == 2:
                await bot.set_group_ban(group_id=group_id, user_id=event.user_id, duration=30*24*60*60)
                action_taken = True
                await matcher.finish(MessageSegment.reply(event.message_id)+f"检测到敏感词，并且已经累计6次违规，将禁言30天")
            elif warn_level >= 3:
                await bot.set_group_kick(group_id=group_id, user_id=event.user_id)
                action_taken = True
                del manager.user_violations[user_id]
                manager.build_ac(group_id)  # 重建当前群的AC自动机
                Handler.load_json(USER_VIOLATIONS_PATH, 'w', manager.user_violations)
                await matcher.finish(MessageSegment.reply(event.message_id)+f"检测到敏感词，并且已经累计9次违规，将踢出该群员")
    # 保存记录
    manager.user_violations[user_id] = violations
    Handler.load_json(USER_VIOLATIONS_PATH, 'w', manager.user_violations)
    if not action_taken:
        await matcher.finish(MessageSegment.reply(event.message_id)+f"检测到敏感词，请文明发言！（累计违规次数：{violations['count']}）")

# 敏感词管理
cmd_add = on_command("添加敏感词", aliases={"敏感词添加"})
cmd_del = on_command("删除敏感词", aliases={"敏感词删除"})
cmd_list = on_command("敏感词列表", aliases={"list_words"})
cmd_group = on_command("敏感词检测", aliases={"敏感词开关"})

@cmd_add.handle()
async def handle_add(event: GroupMessageEvent, args: Message = CommandArg()):  # 限制只能在群内执行
    if not manager.is_admin(str(event.user_id)):
        await cmd_add.finish(MessageSegment.reply(event.message_id)+"权限不足")
    word = args.extract_plain_text().strip()
    if not word:
        await cmd_add.finish(MessageSegment.reply(event.message_id)+"请输入要添加的敏感词")
    
    group_id = str(event.group_id)
    if group_id not in manager.sensitive_words:
        # 初始化数据结构
        manager.sensitive_words[group_id] = {
            "words": set(),
            "admin": []
        }
    
    # 添加操作者到管理员列表
    operator_id = str(event.user_id)
    if operator_id not in manager.sensitive_words[group_id]["admin"]:
        manager.sensitive_words[group_id]["admin"].append(operator_id)

    if word in manager.sensitive_words[group_id]:
        await cmd_add.finish(MessageSegment.reply(event.message_id)+"该敏感词已存在")
    
    manager.sensitive_words[group_id]["words"].add(word)  # ✅ 确保操作的是"words"字段
    
    # 保存到文件
    save_data = {
        gid: {
            "words": list(values["words"]),
            "admin": values.get("admin", [])
        } 
        for gid, values in manager.sensitive_words.items()
    }
    Handler.load_json(SENSITIVE_DATA_PATH, 'w', save_data)
    # 重建当前群的AC自动机
    manager.build_ac(group_id)  # 调用统一封装的构建方法
    await cmd_add.finish(f"已为当前群组添加敏感词：{word}")

@cmd_del.handle()
async def handle_del(event: GroupMessageEvent, args: Message = CommandArg()):  # 限制只能在群内执行
    if not manager.is_admin(str(event.user_id)):
        await cmd_del.finish(MessageSegment.reply(event.message_id)+"权限不足")
    word = args.extract_plain_text().strip()
    if not word:
        await cmd_del.finish(MessageSegment.reply(event.message_id)+"请输入要删除的敏感词")
    
    group_id = str(event.group_id)
    
    # 错误行：group_words = manager.sensitive_words.get(group_id, set())
    # 正确获取敏感词集合
    if group_id not in manager.sensitive_words:
        await cmd_del.finish("该群组未设置敏感词")
    group_words = manager.sensitive_words[group_id]["words"]  # ✅ 获取的是集合

    # 检查敏感词是否存在
    if word not in group_words:
        await cmd_del.finish("该敏感词不存在")

    # 删除操作
    group_words.remove(word)  # ✅ 直接操作集合
    
    # 如果词库为空，清理数据
    if not group_words:
        del manager.sensitive_words[group_id]
        if group_id in manager.ac_dict:
            del manager.ac_dict[group_id]
    else:
        manager.build_ac(group_id)  # ✅ 调用类方法重建自动机
    
    # 保存数据（包含 admin 字段）
    save_data = {
        gid: {
            "words": list(words["words"]),
            "admin": words.get("admin", [])
        }
        for gid, words in manager.sensitive_words.items()
    }
    Handler.load_json(SENSITIVE_DATA_PATH,'w', save_data)
    
    await cmd_del.finish(MessageSegment.reply(event.message_id) + f"已删除敏感词：{word}")

@cmd_list.handle()
async def handle_list(event: GroupMessageEvent):  # 限制只能在群内执行
    group_id = str(event.group_id)
    group_words = manager.sensitive_words.get(group_id, set())
    words = manager.sensitive_words.get(group_id, {}).get("words", set())  # ✅
    word_list = "\n".join(words) if words else "当前群聊暂无敏感词"
    await cmd_list.finish(MessageSegment.reply(event.message_id)+MessageSegment.text(f"当前群组敏感词列表（共{len(words)}个）：\n{word_list}"))

@cmd_group.handle()
async def handle_toggle(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    group_id = str(event.group_id)
    user_id = str(event.user_id)
    action = args.extract_plain_text().strip()
    
    # 无参数时返回当前状态（所有用户可见）
    if not action:
        current_status = "开启" if manager.group_settings.get(group_id, False) else "关闭"
        await cmd_group.finish(MessageSegment.reply(event.message_id)+f"当前群聊的敏感词检测状态：{current_status}")
        return

    # 处理有参数的情况（需要管理员权限）
    if not manager.is_admin(user_id):
        await cmd_group.finish(MessageSegment.reply(event.message_id)+"权限不足，只有敏感词管理员可以操作开关")

    logger.info(f"敏感词检测开关操作：{action}")
    if action in ("开", "开启"):
        manager.group_settings[group_id] = True
        msg = "已在本群启用敏感词检测"
    elif action in ("关", "关闭"):
        manager.group_settings[group_id] = False
        msg = "已在本群禁用敏感词检测"
    else:
        current_status = "开启" if manager.group_settings.get(group_id, False) else "关闭"
        await cmd_group.finish(MessageSegment.reply(event.message_id)+f"参数错误！当前状态：{current_status}\n请使用【开启】或【关闭】")

    Handler.load_json(GROUP_SETTINGS_PATH, 'w', manager.group_settings)
    await cmd_group.finish(MessageSegment.reply(event.message_id)+msg)

