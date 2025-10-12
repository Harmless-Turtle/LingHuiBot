# 标准库导入
import json
from pathlib import Path
from typing import Dict, Set
from datetime import datetime as dt

# 第三方库导入
import ahocorasick

# NoneBot相关导入
from nonebot import get_driver, on_command, on_message
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Bot,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.rule import Rule
from nonebot.log import logger
from nonebot.matcher import Matcher

# 本地模块导入
from src.plugins import utils

# 配置文件路径
DATA_DIR = Path() / "data" / "sensitive_manager"
SENSITIVE_DATA_PATH = DATA_DIR / "sensitive_data.json"
GROUP_SETTINGS_PATH = DATA_DIR / "group_settings.json"
USER_VIOLATIONS_PATH = DATA_DIR / "user_violations.json"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

config = get_driver().config
sensitive_admins = getattr(config, "sensitiveadmin", '[1097740481,1692719245]')
logger.info(f"敏感词管理员列表: {sensitive_admins}")


def ensure_file_exists(file_path: Path, default_content: dict = None):
    """确保文件存在，如果不存在则创建并初始化默认内容"""
    if not file_path.exists():
        logger.warning(f"文件 {file_path} 不存在，正在创建...")
        try:
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入默认内容
            with open(file_path, 'w', encoding='utf-8') as f:
                if default_content is None:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                else:
                    json.dump(default_content, f, ensure_ascii=False, indent=4)
            logger.info(f"已创建文件 {file_path} 并初始化默认内容")
        except Exception as e:
            logger.error(f"创建文件 {file_path} 失败: {e}")
            raise
    return file_path


class SensitiveManager:
    def __init__(self):
        self.ac_dict: Dict[str, ahocorasick.Automaton] = {}
        self.sensitive_words: Dict[str, Set[str]] = {}

        # 确保所有必需文件都存在
        ensure_file_exists(SENSITIVE_DATA_PATH, {})
        ensure_file_exists(GROUP_SETTINGS_PATH, {})
        ensure_file_exists(USER_VIOLATIONS_PATH, {})

        self.load_data()
        self.build_all_ac()

        self.group_settings = utils.handle_json(GROUP_SETTINGS_PATH, 'r') or {}
        # 直接加载新格式的违规记录
        self.group_violations = utils.handle_json(USER_VIOLATIONS_PATH, 'r') or {}

        # 初始化时遍历所有群组构建 AC 自动机
        self.build_all_ac()

        self.group_settings = utils.handle_json(GROUP_SETTINGS_PATH, 'r') or {}
        self.user_violations = utils.handle_json(USER_VIOLATIONS_PATH, 'r') or {}

    def load_data(self):
        data = utils.handle_json(SENSITIVE_DATA_PATH, 'r') or {}
        self.sensitive_words = {}
        for group_id, content in data.items():
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
        words = group_data.get("words", set())
        logger.info(f"正在为群组 {group_id} 构建AC自动机，包含 {len(words)} 个敏感词")
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
async def handle_check(matcher: Matcher, bot: Bot, event: GroupMessageEvent):
    # 跳过管理员的消息
    if manager.is_admin(str(event.user_id)):
        return

    text = event.get_plaintext()
    user_id = str(event.user_id)
    group_id = str(event.group_id)

    # 获取当前群的AC自动机进行检测
    ac = manager.ac_dict.get(group_id)
    found_words = set()
    if ac:
        # 记录当前AC自动机的敏感词数量用于调试
        logger.debug(f"群组 {group_id} 的AC自动机包含 {len(ac)} 个敏感词")
        for _, word in ac.iter(text):
            found_words.add(word)

    if not found_words:
        return

    # 更新违规记录（使用新的以群组为键的数据结构）
    if group_id not in manager.group_violations:
        manager.group_violations[group_id] = {}

    if user_id not in manager.group_violations[group_id]:
        manager.group_violations[group_id][user_id] = {
            "count": 0,
            "warnings": 0,
            "records": []
        }

    violations = manager.group_violations[group_id][user_id]

    # 获取管理员列表并发送通知
    group_info = manager.sensitive_words.get(group_id, {})
    admins = group_info.get("admin", [])
    for admin_id in admins:
        try:
            await bot.send_private_msg(
                user_id=int(admin_id),
                message=f"群{group_id}有用户触发敏感词:\n用户：{event.user_id}\n内容：{text}\n触发词汇：{','.join(found_words)}\n用户已违规次数：{violations["count"] + 1}"
            )
        except Exception as e:
            logger.error(f"通知管理员失败：{e}")

    timestamp = event.time  # 获取整数时间戳（秒级）
    dt_object = dt.fromtimestamp(timestamp)  # 转换为 datetime 对象
    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间

    violations["count"] += 1
    violations["records"].append({
        "time": formatted_time,
        "content": text
    })

    # 处理惩罚逻辑
    action_taken = False
    if violations["count"] % 3 == 0:
        violations["warnings"] += 1
        warn_level = violations["warnings"]
        try:
            Role = await bot.get_group_member_info(group_id=event.group_id, user_id=event.self_id)
            Role = Role['role']
            if Role not in "member":
                if warn_level == 1:
                    await bot.set_group_ban(group_id=group_id, user_id=event.user_id, duration=7 * 24 * 60 * 60)
                    action_taken = True
                    await matcher.finish(
                        MessageSegment.reply(event.message_id) + f"检测到敏感词，并且已经累计3次违规，禁言7天")
                elif warn_level == 2:
                    await bot.set_group_ban(group_id=group_id, user_id=event.user_id, duration=30 * 24 * 60 * 60)
                    action_taken = True
                    await matcher.finish(
                        MessageSegment.reply(event.message_id) + f"检测到敏感词，并且已经累计6次违规，将禁言30天")
                elif warn_level >= 3:
                    await bot.set_group_kick(group_id=group_id, user_id=event.user_id)
                    action_taken = True
                    # 只删除该用户在当前群的记录
                    if group_id in manager.group_violations and user_id in manager.group_violations[group_id]:
                        del manager.group_violations[group_id][user_id]
                    manager.build_ac(group_id)  # 重建当前群的AC自动机
                    utils.handle_json(USER_VIOLATIONS_PATH, 'w', manager.group_violations)
                    await matcher.finish(
                        MessageSegment.reply(event.message_id) + f"检测到敏感词，并且已经累计9次违规，将踢出该群员")
        except Exception as e:
            logger.error(f"执行惩罚时出错：{e}")

    # 保存记录
    utils.handle_json(USER_VIOLATIONS_PATH, 'w', manager.group_violations)
    if not action_taken:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"检测到敏感词，请文明发言！（累计违规次数：{violations['count']}）")


# 敏感词管理
cmd_add = on_command("添加敏感词", aliases={"敏感词添加"})
cmd_del = on_command("删除敏感词", aliases={"敏感词删除"})
cmd_list = on_command("敏感词列表", aliases={"list_words"})
cmd_group = on_command("敏感词检测", aliases={"敏感词开关"})


@cmd_add.handle()
async def handle_add(event: GroupMessageEvent, args: Message = CommandArg()):
    if not manager.is_admin(str(event.user_id)):
        await cmd_add.finish(MessageSegment.reply(event.message_id) + "权限不足")
    word = args.extract_plain_text().strip()
    if not word:
        await cmd_add.finish(MessageSegment.reply(event.message_id) + "请输入要添加的敏感词")

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

    if word in manager.sensitive_words[group_id]["words"]:
        await cmd_add.finish(MessageSegment.reply(event.message_id) + "该敏感词已存在")

    manager.sensitive_words[group_id]["words"].add(word)

    # 保存到文件
    save_data = {
        gid: {
            "words": list(values["words"]),
            "admin": values.get("admin", [])
        }
        for gid, values in manager.sensitive_words.items()
    }
    utils.handle_json(SENSITIVE_DATA_PATH, 'w', save_data)

    # 重建当前群的AC自动机 - 确保立即生效
    manager.build_ac(group_id)
    logger.info(f"已为群组 {group_id} 添加敏感词 '{word}'，并重建AC自动机")

    await cmd_add.finish(f"已为当前群组添加敏感词：{word}")


@cmd_del.handle()
async def handle_del(event: GroupMessageEvent, args: Message = CommandArg()):
    if not manager.is_admin(str(event.user_id)):
        await cmd_del.finish(MessageSegment.reply(event.message_id) + "权限不足")
    word = args.extract_plain_text().strip()
    if not word:
        await cmd_del.finish(MessageSegment.reply(event.message_id) + "请输入要删除的敏感词")

    group_id = str(event.group_id)

    if group_id not in manager.sensitive_words:
        await cmd_del.finish("该群组未设置敏感词")
    group_words = manager.sensitive_words[group_id]["words"]

    if word not in group_words:
        await cmd_del.finish("该敏感词不存在")

    group_words.remove(word)

    if not group_words:
        del manager.sensitive_words[group_id]
        if group_id in manager.ac_dict:
            del manager.ac_dict[group_id]
        logger.info(f"群组 {group_id} 的所有敏感词已删除，AC自动机已移除")
    else:
        # 重建当前群的AC自动机 - 确保立即生效
        manager.build_ac(group_id)
        logger.info(f"已从群组 {group_id} 删除敏感词 '{word}'，并重建AC自动机")

    save_data = {
        gid: {
            "words": list(words["words"]),
            "admin": words.get("admin", [])
        }
        for gid, words in manager.sensitive_words.items()
    }
    utils.handle_json(SENSITIVE_DATA_PATH, 'w', save_data)

    await cmd_del.finish(MessageSegment.reply(event.message_id) + f"已删除敏感词：{word}")


@cmd_list.handle()
async def handle_list(event: GroupMessageEvent):
    group_id = str(event.group_id)
    words = manager.sensitive_words.get(group_id, {}).get("words", set())
    word_list = "\n".join(words) if words else "当前群聊暂无敏感词"
    await cmd_list.finish(MessageSegment.reply(event.message_id) + MessageSegment.text(
        f"当前群组敏感词列表（共{len(words)}个）：\n{word_list}"))


@cmd_group.handle()
async def handle_toggle(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    group_id = str(event.group_id)
    user_id = str(event.user_id)
    action = args.extract_plain_text().strip()

    if not action:
        current_status = "开启" if manager.group_settings.get(group_id, False) else "关闭"
        await cmd_group.finish(MessageSegment.reply(event.message_id) + f"当前群聊的敏感词检测状态：{current_status}")
        return

    if not manager.is_admin(user_id):
        await cmd_group.finish(MessageSegment.reply(event.message_id) + "权限不足，只有敏感词管理员可以操作开关")

    logger.info(f"敏感词检测开关操作：{action}")
    if action in ("开", "开启"):
        manager.group_settings[group_id] = True
        msg = "已在本群启用敏感词检测"
    elif action in ("关", "关闭"):
        manager.group_settings[group_id] = False
        msg = "已在本群禁用敏感词检测"
    else:
        current_status = "开启" if manager.group_settings.get(group_id, False) else "关闭"
        await cmd_group.finish(
            MessageSegment.reply(event.message_id) + f"参数错误！当前状态：{current_status}\n请使用【开启】或【关闭】")

    utils.handle_json(GROUP_SETTINGS_PATH, 'w', manager.group_settings)
    await cmd_group.finish(MessageSegment.reply(event.message_id) + msg)
