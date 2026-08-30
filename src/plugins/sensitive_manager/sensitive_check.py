import asyncio
import json
from datetime import datetime as dt
from typing import Dict, Set

import ahocorasick
from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Bot,
    Message,
    MessageSegment,
)
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.rule import Rule
from nonebot_plugin_orm import async_scoped_session

from .command import cmd_add, cmd_del, cmd_list, cmd_group
from .exceptions import (
    SensitiveError,
    SensitiveGroupNotConfigured,
    SensitivePermissionDenied,
    SensitiveWordExists,
    SensitiveWordNotFound,
)
from .models import (
    add_sensitive_admin,
    add_sensitive_word,
    delete_violation,
    get_violation,
    load_sensitive_settings,
    load_sensitive_words,
    remove_sensitive_word,
    set_sensitive_enabled,
)
from ..utils import handle_errors

config = get_driver().config
sensitive_admins = getattr(config, "sensitiveadmin", '[1097740481,1692719245]')
logger.info(f"敏感词管理员列表: {sensitive_admins}")


def is_admin(user_id: str) -> bool:
    return user_id in sensitive_admins


class SensitiveManager:
    """敏感词管理器：AC 自动机常驻内存，词库/开关/违规记录持久化于 SQLite。"""

    def __init__(self):
        self.ac_dict: Dict[str, ahocorasick.Automaton] = {}
        self.sensitive_words: Dict[str, dict] = {}
        self.group_settings: Dict[str, bool] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    async def ensure_loaded(self, session: async_scoped_session) -> None:
        """首次访问时从数据库加载词库与开关，后续直接命中内存缓存。"""
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            try:
                self.sensitive_words = await load_sensitive_words(session)
                self.group_settings = await load_sensitive_settings(session)
                self.build_all_ac()
                self._loaded = True
                logger.info(f"敏感词数据已从数据库加载：{len(self.sensitive_words)} 个群")
            except Exception as e:
                # 数据库表可能尚未就绪，保留未加载状态以便下次重试
                logger.warning(f"敏感词数据加载失败，将在下次访问时重试：{e}")

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


manager = SensitiveManager()


async def check_enabled(event: GroupMessageEvent, session: async_scoped_session) -> bool:
    await manager.ensure_loaded(session)
    group_id = str(event.group_id)
    return manager.group_settings.get(group_id, False)


sensitive_matcher = on_message(
    rule=Rule(check_enabled),
    priority=10,
    block=False
)


@sensitive_matcher.handle()
async def handle_check(matcher: Matcher, bot: Bot, event: GroupMessageEvent,
                       session: async_scoped_session):
    await manager.ensure_loaded(session)
    # 跳过管理员的消息
    if is_admin(str(event.user_id)):
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

    # 取或建违规记录
    violation = await get_violation(session, group_id, user_id)
    records = json.loads(violation.records) if violation.records else []

    # 获取管理员列表并发送通知
    group_info = manager.sensitive_words.get(group_id, {})
    admins = group_info.get("admin", [])
    for admin_id in admins:
        try:
            await bot.send_private_msg(
                user_id=int(admin_id),
                message=(
                    f"群{group_id}有用户触发敏感词:\n"
                    f"用户：{event.user_id}\n"
                    f"内容：{text}\n"
                    f"触发词汇：{','.join(found_words)}\n"
                    f"用户已违规次数：{violation.count + 1}"
                ),
            )
        except Exception as e:
            logger.error(f"通知管理员失败：{e}")

    timestamp = event.time  # 获取整数时间戳（秒级）
    dt_object = dt.fromtimestamp(timestamp)  # 转换为 datetime 对象
    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间

    violation.count += 1
    records.append({
        "time": formatted_time,
        "content": text
    })
    violation.records = json.dumps(records, ensure_ascii=False)

    # 处理惩罚逻辑
    action_taken = False
    if violation.count % 3 == 0:
        violation.warnings += 1
        warn_level = violation.warnings
        try:
            role = await bot.get_group_member_info(group_id=event.group_id, user_id=event.self_id)
            role = role['role']
            if role not in "member":
                if warn_level == 1:
                    await session.flush()
                    await session.commit()
                    await bot.set_group_ban(group_id=int(group_id), user_id=event.user_id, duration=7 * 24 * 60 * 60)
                    action_taken = True
                    await matcher.finish(
                        MessageSegment.reply(event.message_id) + f"检测到敏感词，并且已经累计3次违规，禁言7天")
                elif warn_level == 2:
                    await session.flush()
                    await session.commit()
                    await bot.set_group_ban(group_id=int(group_id), user_id=event.user_id, duration=30 * 24 * 60 * 60)
                    action_taken = True
                    await matcher.finish(
                        MessageSegment.reply(event.message_id) + f"检测到敏感词，并且已经累计6次违规，将禁言30天")
                elif warn_level >= 3:
                    # 删除该用户在当前群的违规记录
                    await delete_violation(session, group_id, user_id)
                    manager.build_ac(group_id)  # 重建当前群的AC自动机
                    await session.commit()
                    action_taken = True
                    await matcher.finish(
                        MessageSegment.reply(event.message_id) + f"检测到敏感词，并且已经累计9次违规，将踢出该群员")
        except Exception as e:
            logger.error(f"执行惩罚时出错：{e}")

    # 保存记录
    await session.commit()
    if not action_taken:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"检测到敏感词，请文明发言！（累计违规次数：{violation.count}）")


@cmd_add.handle()
@handle_errors
async def handle_add(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    try:
        await manager.ensure_loaded(session)
        if not is_admin(str(event.user_id)):
            raise SensitivePermissionDenied()
        word = args.extract_plain_text().strip()
        if not word:
            await matcher.finish(MessageSegment.reply(event.message_id) + "请输入要添加的敏感词")

        group_id = str(event.group_id)
        if group_id not in manager.sensitive_words:
            # 初始化数据结构
            manager.sensitive_words[group_id] = {
                "words": set(),
                "admin": []
            }

        if word in manager.sensitive_words[group_id]["words"]:
            raise SensitiveWordExists()

        # 添加操作者到管理员列表
        operator_id = str(event.user_id)
        if operator_id not in manager.sensitive_words[group_id]["admin"]:
            manager.sensitive_words[group_id]["admin"].append(operator_id)
            await add_sensitive_admin(session, group_id, operator_id)

        manager.sensitive_words[group_id]["words"].add(word)
        await add_sensitive_word(session, group_id, word)

        # 重建当前群的AC自动机 - 确保立即生效
        manager.build_ac(group_id)
        await session.commit()
        logger.info(f"已为群组 {group_id} 添加敏感词 '{word}'，并重建AC自动机")
    except SensitiveError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(f"已为当前群组添加敏感词：{word}")


@cmd_del.handle()
@handle_errors
async def handle_del(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    try:
        await manager.ensure_loaded(session)
        if not is_admin(str(event.user_id)):
            raise SensitivePermissionDenied()
        word = args.extract_plain_text().strip()
        if not word:
            await matcher.finish(MessageSegment.reply(event.message_id) + "请输入要删除的敏感词")

        group_id = str(event.group_id)

        if group_id not in manager.sensitive_words:
            raise SensitiveGroupNotConfigured()
        group_words = manager.sensitive_words[group_id]["words"]

        if word not in group_words:
            raise SensitiveWordNotFound()

        group_words.remove(word)
        await remove_sensitive_word(session, group_id, word)

        if not group_words:
            del manager.sensitive_words[group_id]
            if group_id in manager.ac_dict:
                del manager.ac_dict[group_id]
            logger.info(f"群组 {group_id} 的所有敏感词已删除，AC自动机已移除")
        else:
            # 重建当前群的AC自动机 - 确保立即生效
            manager.build_ac(group_id)
            logger.info(f"已从群组 {group_id} 删除敏感词 '{word}'，并重建AC自动机")

        await session.commit()
    except SensitiveError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"已删除敏感词：{word}")


@cmd_list.handle()
@handle_errors
async def handle_list(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session
):
    await manager.ensure_loaded(session)
    group_id = str(event.group_id)
    words = manager.sensitive_words.get(group_id, {}).get("words", set())
    word_list = "\n".join(words) if words else "当前群聊暂无敏感词"
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text(
        f"当前群组敏感词列表（共{len(words)}个）：\n{word_list}"))


@cmd_group.handle()
@handle_errors
async def handle_toggle(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    try:
        await manager.ensure_loaded(session)
        group_id = str(event.group_id)
        user_id = str(event.user_id)
        action = args.extract_plain_text().strip()

        if not action:
            current_status = "开启" if manager.group_settings.get(group_id, False) else "关闭"
            await matcher.finish(MessageSegment.reply(event.message_id) + f"当前群聊的敏感词检测状态：{current_status}")

        if not is_admin(user_id):
            raise SensitivePermissionDenied()

        logger.info(f"敏感词检测开关操作：{action}")
        if action in ("开", "开启"):
            manager.group_settings[group_id] = True
            msg = "已在本群启用敏感词检测"
        elif action in ("关", "关闭"):
            manager.group_settings[group_id] = False
            msg = "已在本群禁用敏感词检测"
        else:
            current_status = "开启" if manager.group_settings.get(group_id, False) else "关闭"
            await matcher.finish(
                MessageSegment.reply(event.message_id) +
                f"参数错误！当前状态：{current_status}\n"
                f"请使用【开启】或【关闭】")

        await set_sensitive_enabled(session, group_id, manager.group_settings[group_id])
        await session.commit()
    except SensitiveError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(event.message_id) + msg)
