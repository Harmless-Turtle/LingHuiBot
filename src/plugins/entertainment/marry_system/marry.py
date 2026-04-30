import random as rd
import time
from datetime import datetime

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Message,
    Bot, GroupMessageEvent
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from src.plugins.entertainment.check_files import (
    marry_json_path
)
from src.plugins.entertainment.commands import (
    marry_random,
    finish_marry,
    marry_propose,
    marry_time_check,
    marry_select,
    marry_check,
    marry_switch
)
from src.plugins.utils import handle_errors, handle_json, time_handle, at_is_true


@marry_random.handle()
@handle_errors
async def marry_random_func(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text(): await matcher.finish()
    # 提前准备数据，方便后续调用
    data = handle_json(marry_json_path, 'r')  # 读取结婚系统信息
    user_qq = str(event.user_id)  # 获取用户QQ号
    group_qq = str(event.group_id)  # 获取群号
    user_list = await bot.call_api("get_group_member_list", group_id=event.group_id)  # 群成员列表
    # 如果用户已经存在于data中，则检查是否已有对象或求婚状态存在，如果存在则直接结束事件处理
    if data.get(user_qq, {}).get(group_qq, False):
        text = "你似乎已经有对象了吧...？"
        if data[user_qq].get("request", False) or data[user_qq][group_qq].get("cp_qq", False) == 114514:
            self_data = data[user_qq][group_qq]
            request_mode = self_data['request_mode']
            request = self_data['request']
            stranger_info = await bot.get_stranger_info(user_id=request)
            nickname = stranger_info.get('nickname', '昵称获取失败')
            request_list = [f"向“{nickname}”求婚中", f"被“{nickname}”求婚中"]
            text = f"你当前正在{request_list[request_mode]}\n请先通过“同意/拒绝求婚”或“取消求婚”命令作出决定后再试。"
        await matcher.finish(MessageSegment.reply(event.message_id) + f"{text}")
    # 排除不应该被随机到的用户列表，例如is_robot为True、机器人自身以及用户本身
    exclude_ids = {int(user_qq), event.self_id}
    member_list = [
        x['user_id']
        for x in user_list
        if not x['is_robot'] and x['user_id'] not in exclude_ids
    ]
    # 排除特殊情况：如果群列表人数已为0
    if len(member_list) == 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "呃啊...这个群里好像没有人还可以结婚了qwq")
    # 随机选择一个用户作为对象
    select_qq = member_list[rd.randint(0, len(member_list) - 1)]
    stranger_info = await bot.get_stranger_info(user_id=select_qq)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    # 新建时间戳
    now_time = int(time.time())
    # 构建双方数据并写入文件中存储
    self_json_data = {
        "cp_qq": int(select_qq),
        "time": now_time,
        "request_mode": 0,
        "request": 0,
    }
    select_json_data = {
        "cp_qq": int(user_qq),
        "time": now_time,
        "request_mode": 0,
        "request": 0
    }
    if user_qq not in data:
        data[user_qq] = {}
    if select_qq not in data:
        data[select_qq] = {}
    data[select_qq][group_qq] = select_json_data
    data[user_qq][group_qq] = self_json_data
    handle_json(marry_json_path, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"好嗷~你已经和“{nickname}”【{select_qq}】在一起了呢")


@finish_marry.handle()
@handle_errors
async def finish_marry_func(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    # 若消息后存在其他消息则不响应
    if args.extract_plain_text(): await matcher.finish()
    # 获取用户的QQ，并将值转为str格式
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    # 获取数据
    data = handle_json(marry_json_path, 'r')
    self_data = data.get(self_qq, {}).get(group_id, {})
    # 异常处理
    if not self_data or self_data.get("cp_qq", 114514) == 114514:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎还没有对象吧xwx")
    # 获取对象的QQ号
    cp_qq = str(self_data['cp_qq'])
    stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    time_text = time_handle(self_data['time'])
    # 直接删除用户和用户对象json
    data.pop(self_qq, None)
    data.pop(cp_qq, None)
    # 将处理完的Data写入文件
    handle_json(marry_json_path, 'w', data)
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"你已经和你的群友对象“{nickname}”[{cp_qq}]离婚了呢www\n在一起的时间：{time_text}")


@marry_propose.handle()
@handle_errors
async def marry_propose_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
    # 获取数据
    text = event.get_message()
    user_id, bot_qq, self_qq, timestamp, group_id = event.self_id, event.self_id, event.user_id, int(time.time()), str(
        event.group_id)
    # 获取at值
    user_id = await  at_is_true(event, args)
    logger.info(user_id)
    is_robot = await bot.get_group_member_info(group_id=event.group_id, user_id=int(user_id))
    if user_id == self_qq or user_id == bot_qq or is_robot['is_robot']:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你你...你不可以向自己或者机器人求婚呢xwx")
    # 判断是否为非法请求
    # 获取请求值是否为tx机器人
    temp = str(text)
    if user_id == 0 or user_id == str(event.self_id):
        await matcher.finish(MessageSegment.reply(
            event.message_id) + "凌辉Bot似乎没能理解你要向谁求婚呢...是不是复制了别人的请求呀owo一定要自己@出来哦~/_ \\")
    if "CQ" not in temp and "求婚" in temp:
        await matcher.finish()
    data = handle_json(marry_json_path, 'r')
    target_data = data.get(str(user_id), {}).get(group_id, {})
    if target_data.get("cp_qq", 0) != 0:
        text = "凌辉Bot小声提醒您：您请求的用户似乎已经有对象了awa"
        if target_data.get("request", 0) != 0:
            text = "凌辉Bot小声提醒您：您请求的用户似乎正在被求婚或者求婚其他人呢awa"
        await matcher.finish(MessageSegment.reply(event.message_id) + text)
    self_data_check = data.get(str(self_qq), {}).get(group_id, {})
    if self_data_check.get("cp_qq", 114514) not in (0, 114514):
        await matcher.finish(MessageSegment.reply(event.message_id) + "你已经有对象了啦qwq怎么可以一夫多妻呢/_ \\")
    if self_data_check.get("request", 0) != 0:
        response = self_data_check['request']
        stranger_info = await bot.get_stranger_info(user_id=response)
        request_text = [f"向{stranger_info['nickname']}求婚中", f"被{stranger_info['nickname']}求婚中"]
        request_mode = self_data_check['request_mode']
        await matcher.finish(MessageSegment.reply(event.message_id) + f"你似乎正在{request_text[request_mode]}呢owo")
    # 获取或创建用户数据字典
    self_data = data.setdefault(str(self_qq), {})
    request_data = data.setdefault(str(user_id), {})
    self_count = self_data.get(group_id, {}).get("count", 0)
    cp_count = request_data.get(group_id, {}).get("count", 0)
    # 主动请求人的状态码为0，被请求人的状态码为1
    self_dict = {
        "cp_qq": 114514,
        "request": int(user_id),
        "time": timestamp,
        "request_mode": 0,
        "count": self_count
    }
    request_dict = {
        "cp_qq": 114514,
        "request": self_qq,
        "time": timestamp,
        "request_mode": 1,
        "count": cp_count
    }

    # 更新当前群组数据
    self_data[group_id] = self_dict
    request_data[group_id] = request_dict
    handle_json(marry_json_path, 'w', data)
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"好嗷~你已经向“{nickname}”求婚了哦^_~\n{nickname}[{int(user_id)}]可以通过“同意求婚”或“拒绝求婚”同意或者拒绝求婚请求w")


@marry_select.handle()
@handle_errors
async def marry_select_func(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    text, self_qq, group_id = str(event.get_message()), str(event.user_id), str(event.group_id)
    data = handle_json(marry_json_path, 'r')
    self_data = data.get(self_qq, {}).get(group_id, {})
    if self_data.get("request", 0) == 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎没有被求婚或正在向他人求婚呢owo")
    if self_data.get('cp_qq', 0) not in (0, 114514):
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎已经有对象了吧...？")
    request = self_data['request']
    mode = self_data["request_mode"]
    stranger_info = await bot.get_stranger_info(user_id=request)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    if "拒绝" in text or "取消" in text:
        if not "取消" in text:
            if mode != 1:
                await matcher.finish(MessageSegment.reply(event.message_id) + "这个命令不是你用的吧owo")
        del data[self_qq][group_id], data[str(request)][group_id]
        handle_json(marry_json_path, 'w', data)
        temp = "拒绝"
        temp_1 = ""
        if "取消" in text:
            temp = "取消"
        if mode == 0:
            temp_1 = "对"
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"好叭/_ \\你已经{temp}了{temp_1}“{nickname}”的求婚请求了呢~")
    if mode == 0 and "同意" in text:
        await matcher.finish(MessageSegment.reply(event.message_id) + "这个命令不是你用的吧owo")
    timestamp = int(time.time())
    self_data = data.setdefault(str(self_qq), {})
    request_data = data.setdefault(str(str(request)), {})
    self_count = self_data.get(group_id, {}).get("count", 0)
    cp_count = request_data.get(group_id, {}).get("count", 0)
    self_dict = {
        "cp_qq": request,
        "request": 0,
        "time": timestamp,
        "request_mode": 2,
        "count": self_count
    }
    request_dict = {
        "cp_qq": int(self_qq),
        "request": 0,
        "time": timestamp,
        "request_mode": 2,
        "count": cp_count
    }
    # 获取或创建用户数据字典
    self_data = data.setdefault(str(self_qq), {})
    request_data = data.setdefault(str(request), {})
    # 更新当前群组数据
    self_data[group_id] = self_dict
    request_data[group_id] = request_dict
    handle_json(marry_json_path, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"好哦好哦~（拍爪子）你已经同意“{nickname}”的求婚请求了哦~")


@marry_time_check.handle()
@handle_errors
async def marry_time_check_func(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    data = handle_json(marry_json_path, 'r')
    self_qq, group_id = str(event.user_id), str(event.group_id)
    self_data = data.get(self_qq, {}).get(group_id, {})
    if not self_data or self_data.get("cp_qq", 114514) == 114514:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎还没有对象吧xwx")
    user_id = self_data['cp_qq']
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    time_text = time_handle(self_data['time'])
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"你和群友“{nickname}”[{int(user_id)}]已经在一起{time_text}了呢~")


@marry_check.handle()
@handle_errors
async def marry_check_func(
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        args: Message = CommandArg()
):
    # 读取前置数据
    data = handle_json(marry_json_path, 'r')
    self_qq, group_id, user_id = str(event.user_id), str(event.group_id), 0
    # 获取at值
    user_id = await at_is_true(event, args)
    if user_id != 0:
        self_qq = user_id
    text = "你"
    # 安全获取嵌套值，避免异常
    user_data = data.get(str(self_qq), {}).get(str(group_id), {})
    cp_qq = user_data.get("cp_qq", 0)
    if cp_qq == 114514 or cp_qq == 0:
        logger.info(f"Debug:获取的cp_qq是{cp_qq}，用户id是{user_id}，群组id是{group_id}")
        if str(self_qq) != str(event.user_id):
            await matcher.finish(MessageSegment.reply(event.message_id) + "你查找的群友似乎还没有对象owo")
        await matcher.finish(MessageSegment.reply(event.message_id) + "你似乎还没有对象吧xwx")  # 确定用户合法后读取必要数据
    cp_qq, timestamp = user_data['cp_qq'], user_data['time']
    # 转换为 datetime 对象
    dt_object = datetime.fromtimestamp(timestamp)
    # 获取用户名
    stranger_info = await bot.get_stranger_info(user_id=int(cp_qq))
    nickname = stranger_info.get('nickname', '昵称获取失败')
    # 获取自己的用户名
    if self_qq != str(event.user_id):
        stranger_info_self = await bot.get_stranger_info(user_id=int(self_qq))
        text = stranger_info_self.get('nickname', '昵称获取失败')
    # 获取时间
    time_text = time_handle(timestamp)
    # 最终输出
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"{text}和“{nickname}”[{cp_qq}]在{dt_object.strftime('%Y-%m-%d %H:%M:%S')}时在一起了哦~\n一共在一起{time_text}了呢~")


@marry_switch.handle()
@handle_errors
async def marry_switch_utils(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    # 读取前置数据
    data = handle_json(marry_json_path, 'r')
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    user_data = data.get(self_qq, {}).get(group_id, {})
    cp_qq_val = user_data.get("cp_qq", 0)
    if cp_qq_val != 0:
        cp_qq_str = str(cp_qq_val)
        if cp_qq_val == "114514":
            request = str(user_data.get('request', 0))
            if request in data and group_id in data[request]:
                data[request][group_id].pop("request", None)
                data[request][group_id].pop("request_mode", None)
            user_data.pop("request", None)
            user_data.pop("request_mode", None)
        else:
            if cp_qq_str in data and group_id in data[cp_qq_str]:
                data[cp_qq_str][group_id].pop("cp_qq", None)
                data[cp_qq_str][group_id].pop("time", None)
        user_data.pop("cp_qq", None)
        user_data.pop("time", None)
    # 读取json数据
    data = handle_json(marry_json_path, 'r')
    # 将自己的QQ号转为str格式，方便后续判断
    self_qq = str(event.user_id)
    group_id = str(event.group_id)
    # 生成默认参数
    switch = False
    count = 0
    if data.get(self_qq):
        # 读取计数器信息，并进行次数限制判断
        count_json = data[self_qq].get(group_id, False)
        logger.info(count_json)
        if count_json:
            now = datetime.fromtimestamp(int(time.time()))
            self_time = datetime.fromtimestamp(count_json['time'])
            if now.day != self_time.day or now.month != self_time.month:
                logger.info("重置计数器")
                # 如果当前时间和上次请求时间不在同一天，则重置计数器
                count_json['count'] = 0
                count_json['switch'] = True
                logger.info("Reset")
            if count_json.get('switch', False):
                switch = count_json['switch']
                logger.info(f"获取Switch：{switch}")
            count = count_json['count']
        if count > 3:
            logger.info("已经达到了请求次数上限啦！本次跳过执行")
            if switch:
                count_json['switch'] = False
                logger.info(f"写入数据：{count_json}")
                handle_json(marry_json_path, 'w', count_json)
                await matcher.finish(MessageSegment.reply(
                    event.message_id) + "你已经结婚太多次了啦！第二天再结~\n（免打扰模式已开启，您在重置时间前只会看到此消息1次）")
            await matcher.finish()

    # 初步生成排除列表，将已存在的key（即已经有对象的人）和bot以及用户加入到排除列表中，并转化为整数方便进行判断
    exclusion_list = [int(key) for key in data.keys() if
                      data[key].get(group_id, False) and data[key][group_id].get("cp_qq", 0)]
    # 将bot和用户加入到排除列表中
    exclusion_list.extend([event.self_id, event.user_id])
    # 生成群成员列表
    group_user_list = await bot.call_api("get_group_member_list", group_id=event.group_id)
    # 生成随机取值的基列
    data_list = [x['user_id'] for x in group_user_list if x['user_id'] not in exclusion_list and not x['is_robot']]
    # 生成随机数，并获取对应的QQ号
    if len(data_list) - 1 == 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "这个群好像没有其他人了呢...")
    random_select = data_list[rd.randint(0, len(data_list) - 1)]
    # 生成时间戳
    timestamp = int(time.time())
    logger.info(f"Debug:计数器：{count}")
    # 安全写入，避免覆盖其他群组数据
    data.setdefault(str(random_select), {})[group_id] = {"cp_qq": event.user_id, "time": timestamp}
    data.setdefault(str(self_qq), {})[group_id] = {"cp_qq": random_select, "time": timestamp, "count": count + 1,
                                                   "switch": True}
    # 写入文件
    handle_json(marry_json_path, 'w', data)
    # 获取结束事件处理所必要的讯息
    stranger_info = await bot.get_stranger_info(user_id=random_select)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    text = ""
    if count == 2:
        text = "不要老是换群友老婆啦笨蛋！\n"
    elif count == 3:
        text = "再换今天就不给你找群友老婆了！\n"
    # 结束事件处理
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"{text}好嗷~你已经和“{nickname}”【{random_select}】在一起了呢")
