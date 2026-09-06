import random as rd
from datetime import datetime, timedelta, timezone

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Message,
    Bot, GroupMessageEvent
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from src.plugins.entertainment.marry_system.exceptions import (
    MarryAlreadyMarried,
    MarryError,
    MarryLimitReached,
    MarryNoCandidate,
    MarryNotMarried,
)
from src.plugins.entertainment.marry_system.models import (
    MarryMode,
    delete_marry_record,
    get_marry_record,
    get_or_create_marry_record,
    get_partnered_user_ids_in_group,
)
from src.plugins.entertainment.commands import (
    marry_random,
    finish_marry,
    marry_propose,
    marry_select,
    marry_check,
    marry_switch
)
from src.plugins.utils import at_is_true, handle_errors, time_handle, utc_now


def _to_epoch(utc_dt: datetime) -> int:
    """naive UTC datetime -> epoch 秒（time_handle 需要 epoch 时间戳）。"""
    return int(utc_dt.replace(tzinfo=timezone.utc).timestamp())


DAILY_SWITCH_LIMIT = 3  # “换老婆”当日上限次数


@marry_random.handle()
@handle_errors
async def marry_random_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text(): await matcher.finish()
    try:
        # 提前准备数据，方便后续调用
        user_qq = str(event.user_id)  # 获取用户QQ号
        group_qq = str(event.group_id)  # 获取群号
        user_list = await bot.call_api("get_group_member_list", group_id=event.group_id)  # 群成员列表
        # 读取本人记录：仅单身（SINGLE）可以随机配对，已婚/求婚中直接结束
        self_rec = await get_marry_record(session, user_qq, group_qq)
        if self_rec is not None:
            match self_rec.request_mode:
                case MarryMode.SINGLE:
                    pass
                case MarryMode.MARRIED:
                    await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎已经有对象了吧...？")
                case MarryMode.ACTIVE_PROPOSE | MarryMode.PASSIVE_PROPOSE:
                    request = self_rec.request
                    stranger_info = await bot.get_stranger_info(user_id=request)
                    nickname = stranger_info.get('nickname', '昵称获取失败')
                    match self_rec.request_mode:
                        case MarryMode.ACTIVE_PROPOSE:
                            await matcher.finish(MessageSegment.reply(event.message_id) +
                                                 f"你当前正在向“{nickname}”求婚中\n请先通过“同意/拒绝求婚”或“取消求婚”命令作出决定后再试。")
                        case MarryMode.PASSIVE_PROPOSE:
                            await matcher.finish(MessageSegment.reply(event.message_id) +
                                                 f"你当前正在被“{nickname}”求婚中\n请先通过“同意/拒绝求婚”或“取消求婚”命令作出决定后再试。")
        # 排除不应该被随机到的用户列表：机器人、bot 自身、用户本身，
        # 以及本群已婚/求婚中的用户（不抢已有对象的群友）
        exclude_ids = {int(user_qq), event.self_id}
        partnered = await get_partnered_user_ids_in_group(session, group_qq)
        exclude_ids.update(int(x) for x in partnered)
        member_list = [
            x['user_id']
            for x in user_list
            if not x['is_robot'] and x['user_id'] not in exclude_ids
        ]
        # 排除特殊情况：如果群列表人数已为0
        if len(member_list) == 0:
            raise MarryNoCandidate("呃啊...这个群里好像没有人还可以结婚了qwq")
        # 随机选择一个用户作为对象
        select_qq = member_list[rd.randint(0, len(member_list) - 1)]
        stranger_info = await bot.get_stranger_info(user_id=select_qq)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        # 新建时间戳（标准 UTC，naive datetime）
        now_time = utc_now()
        # 构建双方数据并写入数据库
        self_rec = await get_or_create_marry_record(session, user_qq, group_qq)
        select_rec = await get_or_create_marry_record(session, str(select_qq), group_qq)
        self_rec.request_mode = MarryMode.MARRIED
        self_rec.cp_qq = int(select_qq)
        self_rec.request = 0
        self_rec.time = now_time
        select_rec.request_mode = MarryMode.MARRIED
        select_rec.cp_qq = int(user_qq)
        select_rec.request = 0
        select_rec.time = now_time
        await session.flush()
        await session.commit()
    except MarryError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"好嗷~你已经和“{nickname}”【{select_qq}】在一起了呢")


@finish_marry.handle()
@handle_errors
async def finish_marry_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text(): await matcher.finish()
    try:
        # 获取用户的QQ，并将值转为str格式
        self_qq = str(event.user_id)
        group_id = str(event.group_id)
        # 获取数据
        self_rec = await get_marry_record(session, self_qq, group_id)
        # 异常处理：无记录或尚未已婚（单身/仍在求婚中）
        if self_rec is None:
            raise MarryNotMarried()
        match self_rec.request_mode:
            case MarryMode.MARRIED:
                pass
            case _:
                raise MarryNotMarried()
        # 获取对象的QQ号
        cp_qq = str(self_rec.cp_qq)
        stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
        nickname = stranger_info.get('nickname', '昵称获取失败')
        time_text = time_handle(_to_epoch(self_rec.time))
        # 删除本人与对象的记录
        await delete_marry_record(session, self_qq, group_id)
        await delete_marry_record(session, cp_qq, group_id)
        await session.commit()
    except MarryError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"你已经和你的群友对象“{nickname}”[{cp_qq}]离婚了呢www\n在一起的时间：{time_text}")


@marry_propose.handle()
@handle_errors
async def marry_propose_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    try:
        # 获取数据
        text = event.get_message()
        bot_qq, self_qq = event.self_id, event.user_id
        timestamp = utc_now()  # 标准 UTC
        group_id = str(event.group_id)
        # 获取at值
        user_id = await at_is_true(event)
        if not user_id.isdigit():
            await matcher.finish(MessageSegment.reply(event.message_id) + "凌辉Bot似乎没能理解你要向谁求婚呢...是不是复制了别人的请求呀owo一定要自己@出来哦~/_ \\")
        is_robot = await bot.get_group_member_info(group_id=event.group_id, user_id=int(user_id))
        if user_id == str(self_qq) or user_id == str(bot_qq) or is_robot['is_robot']:
            await matcher.finish(MessageSegment.reply(event.message_id) + "你你...你不可以向自己或者机器人求婚呢xwx")
        # 判断是否为非法请求
        temp = str(text)
        if "CQ" not in temp and "求婚" in temp:
            await matcher.finish()
        # 检查目标是否已有对象或正在求婚
        target_rec = await get_marry_record(session, str(user_id), group_id)
        if target_rec is not None:
            match target_rec.request_mode:
                case MarryMode.SINGLE:
                    pass
                case MarryMode.MARRIED:
                    raise MarryAlreadyMarried("凌辉Bot小声提醒您：您请求的用户似乎已经有对象了awa")
                case MarryMode.ACTIVE_PROPOSE | MarryMode.PASSIVE_PROPOSE:
                    raise MarryAlreadyMarried("凌辉Bot小声提醒您：您请求的用户似乎正在被求婚或者求婚其他人呢awa")
        # 检查自己是否已有对象或正在求婚
        self_rec = await get_marry_record(session, str(self_qq), group_id)
        if self_rec is not None:
            match self_rec.request_mode:
                case MarryMode.SINGLE:
                    pass
                case MarryMode.MARRIED:
                    raise MarryAlreadyMarried("你已经有对象了啦qwq怎么可以一夫多妻呢/_ \\")
                case MarryMode.ACTIVE_PROPOSE:
                    response = self_rec.request
                    stranger_info = await bot.get_stranger_info(user_id=response)
                    await matcher.finish(MessageSegment.reply(event.message_id) +
                                         f"你似乎正在向{stranger_info['nickname']}求婚中呢owo")
                case MarryMode.PASSIVE_PROPOSE:
                    response = self_rec.request
                    stranger_info = await bot.get_stranger_info(user_id=response)
                    await matcher.finish(MessageSegment.reply(event.message_id) +
                                         f"你似乎正在被{stranger_info['nickname']}求婚中呢owo")
        # 获取或创建双方记录
        self_count = self_rec.count if self_rec is not None else 0
        cp_count = target_rec.count if target_rec is not None else 0
        self_rec = await get_or_create_marry_record(session, str(self_qq), group_id)
        target_rec = await get_or_create_marry_record(session, str(user_id), group_id)
        # 主动请求人为 ACTIVE_PROPOSE，被请求人为 PASSIVE_PROPOSE；求婚中无对象（cp_qq=0）
        self_rec.request_mode = MarryMode.ACTIVE_PROPOSE
        self_rec.cp_qq = 0
        self_rec.request = int(user_id)
        self_rec.time = timestamp
        self_rec.count = self_count
        target_rec.request_mode = MarryMode.PASSIVE_PROPOSE
        target_rec.cp_qq = 0
        target_rec.request = self_qq
        target_rec.time = timestamp
        target_rec.count = cp_count
        await session.flush()
        await session.commit()
        stranger_info = await bot.get_stranger_info(user_id=int(user_id))
        nickname = stranger_info.get('nickname', '昵称获取失败')
    except MarryError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"好嗷~你已经向“{nickname}”求婚了哦^_~\n{nickname}[{int(user_id)}]可以通过“同意求婚”或“拒绝求婚”同意或者拒绝求婚请求w")


@marry_select.handle()
@handle_errors
async def marry_select_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    try:
        text, self_qq, group_id = str(event.get_message()), str(event.user_id), str(event.group_id)
        self_rec = await get_marry_record(session, self_qq, group_id)
        if self_rec is None:
            raise MarryNotMarried("你似乎没有被求婚或正在向他人求婚呢owo")
        # 只有处于求婚中（ACTIVE/PASSIVE_PROPOSE）才能同意/拒绝/取消
        mode = self_rec.request_mode
        match mode:
            case MarryMode.MARRIED:
                raise MarryAlreadyMarried()
            case MarryMode.SINGLE:
                raise MarryNotMarried("你似乎没有被求婚或正在向他人求婚呢owo")
            case MarryMode.ACTIVE_PROPOSE | MarryMode.PASSIVE_PROPOSE:
                pass
        request = self_rec.request
        stranger_info = await bot.get_stranger_info(user_id=request)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        if "拒绝" in text or "取消" in text:
            if "取消" not in text:
                # 只有被求婚方（PASSIVE_PROPOSE）可以执行“拒绝”
                match mode:
                    case MarryMode.PASSIVE_PROPOSE:
                        pass
                    case _:
                        await matcher.finish(MessageSegment.reply(event.message_id) + "这个命令不是你用的吧owo")
            await delete_marry_record(session, self_qq, group_id)
            await delete_marry_record(session, str(request), group_id)
            await session.commit()
            temp = "拒绝"
            temp_1 = ""
            if "取消" in text:
                temp = "取消"
            match mode:
                case MarryMode.ACTIVE_PROPOSE:
                    temp_1 = "对"
            await matcher.finish(
                MessageSegment.reply(event.message_id) + f"好叭/_ \\你已经{temp}了{temp_1}“{nickname}”的求婚请求了呢~")
        if "同意" in text:
            # 主动求婚方（ACTIVE_PROPOSE）不能执行“同意”
            match mode:
                case MarryMode.ACTIVE_PROPOSE:
                    await matcher.finish(MessageSegment.reply(event.message_id) + "这个命令不是你用的吧owo")
                case _:
                    pass
        timestamp = utc_now()  # 标准 UTC
        self_count = self_rec.count
        request_rec = await get_marry_record(session, str(request), group_id)
        # 双向校验：对方应仍处于 ACTIVE_PROPOSE 且 request 指向本人，
        # 否则说明求婚已被取消/对方状态已变，本次同意视为失效
        if request_rec is None or request_rec.request_mode != MarryMode.ACTIVE_PROPOSE \
                or request_rec.request != int(self_qq):
            await delete_marry_record(session, self_qq, group_id)
            await delete_marry_record(session, str(request), group_id)
            await session.commit()
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 "似乎对方已经取消了求婚呢...让TA重新求婚一次吧owo")
        cp_count = request_rec.count
        self_rec.request_mode = MarryMode.MARRIED
        self_rec.cp_qq = request
        self_rec.request = 0
        self_rec.time = timestamp
        self_rec.count = self_count
        request_rec.request_mode = MarryMode.MARRIED
        request_rec.cp_qq = int(self_qq)
        request_rec.request = 0
        request_rec.time = timestamp
        request_rec.count = cp_count
        await session.flush()
        await session.commit()
    except MarryError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"好哦好哦~（拍爪子）你已经同意“{nickname}”的求婚请求了哦~")


@marry_check.handle()
@handle_errors
async def marry_check_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    try:
        # 读取前置数据
        self_qq, group_id = str(event.user_id), str(event.group_id)
        # 获取at值：无 @ 查自己；非法复制提示；有效 @ 查群友
        user_id = await at_is_true(event)
        if user_id == "illegal":
            await matcher.finish(MessageSegment.reply(event.message_id) + "这个 @ 似乎来路不明呀...像是复制粘贴的owo")
        if user_id != "finish":
            self_qq = user_id
        text = "你"
        # 安全获取记录，避免异常：仅已婚（MARRIED）可以查询婚姻时间
        user_rec = await get_marry_record(session, str(self_qq), str(group_id))
        if user_rec is None:
            if str(self_qq) != str(event.user_id):
                raise MarryNotMarried("你查找的群友似乎还没有对象owo")
            raise MarryNotMarried()  # 确定用户合法后读取必要数据
        match user_rec.request_mode:
            case MarryMode.MARRIED:
                pass
            case _:
                if str(self_qq) != str(event.user_id):
                    raise MarryNotMarried("你查找的群友似乎还没有对象owo")
                raise MarryNotMarried()  # 确定用户合法后读取必要数据
        cp_qq = user_rec.cp_qq
        timestamp = user_rec.time  # UTC datetime
        # 转换为 UTC+8 本地时间显示
        dt_object = timestamp + timedelta(hours=8)
        # 获取用户名
        stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
        nickname = stranger_info.get('nickname', '昵称获取失败')
        # 获取自己的用户名
        if self_qq != str(event.user_id):
            stranger_info_self = await bot.get_stranger_info(user_id=int(self_qq))
            text = stranger_info_self.get('nickname', '昵称获取失败')
        # 获取时间
        time_text = time_handle(_to_epoch(timestamp))
    except MarryError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    # 最终输出
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"{text}和“{nickname}”[{cp_qq}]在{dt_object.strftime('%Y-%m-%d %H:%M:%S')}时在一起了哦~\n一共在一起{time_text}了呢~")


@marry_switch.handle()
@handle_errors
async def marry_switch_utils(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    try:
        # 读取前置数据
        self_qq = str(event.user_id)
        group_id = str(event.group_id)
        self_rec = await get_marry_record(session, self_qq, group_id)
        # 换老婆的前提：本人已婚
        if self_rec is None:
            raise MarryNotMarried()
        match self_rec.request_mode:
            case MarryMode.MARRIED:
                pass
            case _:
                raise MarryNotMarried()
        # 生成默认参数
        switch = False
        count = 0
        # 读取计数器信息，并进行次数限制判断（时间均为 UTC naive datetime）
        now = utc_now()
        self_time = self_rec.time
        # 换日重置判断：完整年月日才能判定是否为“同一天”（None 视为无重置依据）
        if self_time is not None and (now.year, now.month, now.day) != (self_time.year, self_time.month, self_time.day):
            logger.info("重置计数器")
            # 如果当前时间和上次请求时间不在同一天，则重置计数器
            self_rec.count = 0
            self_rec.switch = True
        if self_rec.switch:
            switch = self_rec.switch
            logger.info(f"获取Switch：{switch}")
        count = self_rec.count
        if count > DAILY_SWITCH_LIMIT:
            logger.info("已经达到了请求次数上限啦！本次跳过执行")
            if switch:
                self_rec.switch = False
                await session.commit()
                raise MarryLimitReached(
                    "你已经结婚太多次了啦！第二天再结~\n"
                    "（免打扰模式已开启，您在重置时间前只会看到此消息1次）")
            await matcher.finish()

        # 初步生成排除列表：该群中已婚或求婚中的用户（request_mode != SINGLE），以及 bot 与用户本人
        exclusion_list = await get_partnered_user_ids_in_group(session, group_id)
        exclusion_set = {int(x) for x in exclusion_list}
        exclusion_set.update({event.self_id, event.user_id})
        # 生成群成员列表
        group_user_list = await bot.call_api("get_group_member_list", group_id=event.group_id)
        # 生成随机取值的基列
        data_list = [x['user_id'] for x in group_user_list if x['user_id'] not in exclusion_set and not x['is_robot']]
        # 生成随机数，并获取对应的QQ号
        if len(data_list) == 0:
            raise MarryNoCandidate()
        random_select = data_list[rd.randint(0, len(data_list) - 1)]
        # 生成时间戳（标准 UTC）
        timestamp = utc_now()
        # 写入双方记录
        self_rec = await get_or_create_marry_record(session, self_qq, group_id)
        partner_rec = await get_or_create_marry_record(session, str(random_select), group_id)
        partner_rec.request_mode = MarryMode.MARRIED
        partner_rec.cp_qq = event.user_id
        partner_rec.request = 0
        partner_rec.time = timestamp
        partner_rec.count = 0
        partner_rec.switch = False
        self_rec.request_mode = MarryMode.MARRIED
        self_rec.cp_qq = random_select
        self_rec.request = 0
        self_rec.time = timestamp
        self_rec.count = count + 1
        self_rec.switch = True
        # 写入数据库
        await session.flush()
        await session.commit()
        # 获取结束事件处理所必要的讯息
        stranger_info = await bot.get_stranger_info(user_id=random_select)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        text = ""
        if count == 2:
            text = "不要老是换群友老婆啦笨蛋！\n"
        elif count == 3:
            text = "再换今天就不给你找群友老婆了！\n"
    except MarryError as e:
        await session.rollback()
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    # 结束事件处理
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"{text}好嗷~你已经和“{nickname}”【{random_select}】在一起了呢")
