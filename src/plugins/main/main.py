import random as rd
import time
from datetime import datetime as dt

import httpx
from nonebot import get_driver
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    Message,
    Bot,
)
from nonebot.exception import ActionFailed
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from .check_file import *
from .commands import *
from ..entertainment.currency.models import get_mohui_data, add_mohui_coin
from ..utils import handle_errors

# 获取机器人的名字
config = get_driver().config
try:
    nickname = config.nickname
except AttributeError:
    logger.warning("未加载到NICKNAME配置，请前往dotEnv文件新建该配置项，否则部分功能可能不可用")

# 定义全局变量
poke_count = 0
time_count = time.time()
send = True
at_count = 0
at_time = time.time()


@poke_check.handle()
@handle_errors
async def pc_function(matcher: Matcher):
    global poke_count, time_count, send
    if poke_count >= 3 and time.time() - time_count <= 120:
        if time.time() - time_count >= 120:
            poke_count = 0
            await pc_function(matcher)
        else:
            if send:
                send = False
                await matcher.finish("呜呜...不可以再捏了~（2分钟后可以继续捏~）")
            else:
                pass
    else:
        send = True
        text_list = handle_json(poke_path, 'r')

        poke_count += 1
        time_count = time.time()
        random_message = text_list[rd.randint(0, len(text_list) - 1)]
        await matcher.finish(f"{random_message}")


@add_welcome.handle()
@handle_errors
async def welcome(matcher: Matcher, event: GroupIncreaseNoticeEvent):
    if event.user_id == event.self_id: await matcher.finish()
    welcome_dict = handle_json(welcome_path, 'r')
    group_id = str(event.group_id)
    if welcome_dict.get(group_id, False):
        group_dict = welcome_dict[f'{group_id}']
        if not group_dict['mode']:
            await matcher.finish()
        if group_dict.get("Text", False):
            return_text = welcome_dict[f"{group_id}"]['Text']
            await matcher.finish(f"{return_text}")
        else:
            await matcher.finish(
                "新人记得给群主早上请安晚上侍寝（bushi\n"
                "欢迎新成员加入本群！凌辉Bot欢迎您~\n"
                "Welcome new members to join this family! Linghui Bot welcomes you~")
    else:
        await matcher.finish()


@SelfJoinGroupWelcome.handle()
@handle_errors
async def self_join_group_welcome_function(matcher: Matcher, event: GroupIncreaseNoticeEvent):
    if event.user_id == event.self_id:
        await matcher.finish(
            "嗷呜~感谢您使用凌辉Bot~我可以给你提供Furry的相关功能，以及一些其他的功能哦~\n"
            "如果您想要了解更多功能，请输入“菜单”来获取帮助信息哦~\n"
            "如果您担心与群里其他Bot的命令冲突，可以通过“凌辉菜单”来使用菜单哦www~希望您能喜欢我~\n"
            "如果您有任何问题，请随时联系管理员[1097740481]哦~\n"
            "如果在使用过程中出现了问题，可以通过命令“bug反馈“来直接发送给开发者\n"
            "使用命令“用户协议”可以查看凌辉Bot用户协议")
    else:
        pass


@a_word.handle()
@handle_errors
async def a_word_function(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    word_list = handle_json(aword_path, 'r')

    result = word_list[rd.randint(0, len(word_list) - 1)]
    await matcher.finish(MessageSegment.reply(event.message_id) + f"“{result}”")


# 签到触发器与实现
@sign_in.handle()
@handle_errors
async def sign_in_function(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    # 若签到文本后有文本，则直接结束任务
    if args.extract_plain_text(): await matcher.finish()
    # 打开文件并写入Sign_Dict字典
    sign_dict = handle_json(sign_in_path, 'r')
    # 获取触发人QQ号和群聊号
    user, group = event.user_id, event.group_id
    # 获取触发时间
    from datetime import date
    time_normal = str(date.today())
    time_normal = time_normal.split("-")  # 切片->构建基本时间
    current_day = int(time_normal[-1])  # 获取签到天数
    month = int(time_normal[-2])  # 获取签到月份
    # 生成默认参数
    group_time, group_month, group_count, group_user_list = current_day, month, 0, {}
    user_time, user_count, user_month, text, user_greenwich_time = current_day, 0, month, "", 0
    # 判断：群聊是否已经存在数据
    if sign_dict.get(f"{group}"):  # 如果存在数据，则读取它，顺便处理。
        logger.info("找到群聊数据，开始处理")
        group_dict = sign_dict[f'{group}']
        group_time, group_month, group_count, group_user_list = group_dict['Time'], group_dict['Month'], group_dict[
            'Count'], group_dict['User_Dict']
        # 判断：群聊最后一次签到时间是否已经超过一天
        if current_day != group_time:  # 如果已经超过了一天，则重置状态。
            group_time, group_month, group_count = current_day, month, 0
        elif month != group_month:
            group_time, group_month, group_count, group_user_list = current_day, month, 0, {}
        # 判断：数据内是否已经存在了用户数据
        if group_user_list.get(str(user)):  # 如果不为空，则读取数据
            logger.info("找到个人数据，开始处理")
            user_info = group_user_list.get(str(user))
            user_time, user_count, user_month, user_greenwich_time = user_info["Time"], user_info['Count'], user_info[
                "Month"], user_info['Greenwich_Time']
            if current_day == user_time and month == user_month:
                await matcher.finish(MessageSegment.reply(event.message_id) + "你今天已经在本群签到啦~")
        # 判断：用户最后一次签到时间是否已超过一个月
        if user_month != month:  # 如果已经超过了一个月，则重置状态
            user_time, user_count, user_month = current_day, 0, month
    # 处理数据
    group_count += 1
    user_count += 1
    greenwich_time = int(time.time())
    # 构建信息
    new_sign_user_dict = {
        "Count": user_count,
        "Time": current_day,
        "Month": month,
        "Greenwich_Time": greenwich_time
    }
    new_sign_group_dict = {
        "Time": group_time,
        "Count": group_count,
        "Month": group_month,
        "User_Dict": group_user_list
    }
    group_user_list[f"{user}"] = new_sign_user_dict
    sign_dict[f'{group}'] = new_sign_group_dict
    # 将构建完成的信息写入本地json文件进行保存
    handle_json(sign_in_path, 'w', sign_dict)
    a_word_list = handle_json(aword_path, 'r')
    result = a_word_list[rd.randint(0, len(a_word_list) - 1)]
    # 判断随机给墨辉币的数量
    rd_coins = rd.randint(50, 300)
    operate_coins = user_count * 2 + rd_coins
    await add_mohui_coin(session, str(event.user_id), operate_coins)
    await session.commit()
    obj = await get_mohui_data(session, str(event.user_id))
    balance = obj.mohui_coin
    # 判断：调用是否出现“好久不见”字样
    if "好久不见" in str(event.message):
        # 生成检测到“好久不见”字样的默认值
        text = "诶...好像也没有太久吧~是不是记错时间了呀~\n"
        pic = sign_in_pic_false
        # 判断：如果读取用户的格林威治时间戳减去当前时间戳大于或等于259200秒（即3天整），则更改输出条件。
        if (greenwich_time - user_greenwich_time) >= 259200:
            text = "确实好久不见了诶~抱抱~\n"
            pic = sign_in_pic_true
        # 输出
        await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(
            pic) + f"{text}签到成功。本月在本群中已签到{user_count}次，今天在本群中排名第{group_count}位~\n"
                   f"您获得了{operate_coins}个墨辉币！您现在有{balance}个墨辉币。\n"
                   f"——————\n"
                   f"“{result}”")
    # 输出
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"{text}签到成功。您本月在本群中已签到{user_count}次，今天在本群中排名第{group_count}位。\n"
                            f"您获得了{operate_coins}个墨辉币！您现在有{balance}个墨辉币。\n"
                            f"——————\n"
                            f"“{result}”")


@btfrk.handle()
@handle_errors
async def wc_btfrk(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
    match = re.search(r"我是(.+)控", event.message.extract_plain_text())
    members = await bot.get_group_member_list(group_id=event.group_id)
    if len(match.group(1)) < 2 or match.group(1) in ['福瑞', 'furry', 'Furry', '兽人', '售人']: await matcher.finish()
    filtered_member_names = [item for member in members if not member['is_robot'] for item in
                             (member["nickname"], member['card'], member["title"]) if not item == ""]
    select = None
    select_qq = None
    try:
        for name in filtered_member_names:
            if match.group(1) in name:
                select = name
        if select is None:
            await matcher.finish("未找到")
            return
        for i in members:
            if i['nickname'] == select or i['card'] == select or i['title'] == select:
                select_qq = int(i['user_id'])
    except Exception as e:
        logger.error(e)

    if select_qq is None:
        await matcher.finish("未找到")
        return

    user_card = MessageSegment.contact_user(select_qq)
    message = Message([
        MessageSegment.text("推荐用户"),
        user_card
    ])
    await btfrk.finish(message)


@like_friend.handle()
@handle_errors
async def lf_function(matcher: Matcher, event: NoticeEvent):
    from nonebot import get_bot
    bot = get_bot()
    data = event.model_dump()
    user_data = handle_json(friend_like_path, 'r')
    user_id = data['operator_id']
    now = dt.now()
    day = now.day
    dict_day = day
    if not user_data.get(f"{user_id}", False):
        user_data[f"{user_id}"] = {'Model': True, "Time": dict_day}
        logger.info("新建用户数据！")
    dict_day = user_data[f"{user_id}"]['Time']
    if day != dict_day:
        user_data[f"{user_id}"]['Time'] = day
        user_data[f"{user_id}"]['Model'] = True
        logger.info("不是同一天，进行覆写！")
    model = user_data[f"{user_id}"]['Model']
    if not model:
        await matcher.finish()
    try:
        await bot.send_like(user_id=user_id, times=10)
    except ActionFailed:
        pass
    text = f"owo？是你给我点赞了嘛~谢谢~\n凌辉也给你点赞哦~（如果已经点过了那就不点了呐~嘻嘻ww）"
    user_data[f"{user_id}"]['Model'] = False
    user_data[f"{user_id}"]['Time'] = day
    handle_json(friend_like_path, 'w', user_data)
    try:
        if user_id != 1097740481:
            await bot.send_private_msg(user_id=user_id, message=text)
            logger.info("已经回赞完毕")
    except ActionFailed:
        logger.error(f"发送点赞消息失败，可能是因为没有添加好友")


@add_friend.handle()
@handle_errors
async def af_function(bot: Bot, matcher: Matcher, event: FriendRequestEvent):
    request_type, user_id, flag, comment = event.request_type, event.user_id, event.flag, event.comment
    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
    user_nickname = stranger_info.get('nickname', '昵称获取失败')
    friend_request_message = (
        f"发现新用户试图添加Bot为好友，请查看参数后决定是否批准Bot添加好友。\n"
        f"用户参数如下：\n"
        f"加好友请求来源：{request_type}\n"
        f"QQ资料卡昵称：{user_nickname}\n"
        f"QQ号：{user_id}\n"
        f"加好友理由：{comment}\n"
        f"请求唯一id号：{flag}\n"
        f"您可以通过“同意{flag}”或“拒绝{flag}”来处理此请求。"
    )
    await bot.send_private_msg(user_id=1097740481, message=friend_request_message)
    await matcher.finish()


@choice_friend.handle()
async def cf_function(matcher: Matcher, event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    if "同意" in str(event.get_message):
        select = True
    elif "拒绝" in str(event.get_message):
        select = False
    else:
        await matcher.finish(MessageSegment.reply(event.message_id) + "命令不正确")
        return

    try:
        await bot.set_friend_add_request(flag=str(args), approve=select)
        await matcher.finish(MessageSegment.reply(event.message_id) + "已经处理了此好友请求。")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到对应的flag，请检查flag是否正确。")


@like.handle()
async def like_function(bot: Bot, matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    try:
        random_number = rd.randint(1, 10)
        await bot.send_like(user_id=event.user_id, times=10)
        if random_number == 1:
            await matcher.finish(MessageSegment.reply(event.message_id) + "诶嘿~我不点ww~")
        else:
            await matcher.finish(MessageSegment.reply(event.message_id) + "好好~给你点~但是我一天最多只能点10个哦w")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id) + "凌辉今天已经给你点过赞了啦qwq...不能再点了哦~")


@eat_what.handle()
async def eat_function(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    if str(args) != "":
        group_member_list = await bot.get_group_member_list(group_id=event.group_id)
        random_choice = group_member_list[rd.randint(0, len(group_member_list) - 1)]
        selected_nickname = random_choice['nickname']
        user_id = random_choice['user_id']
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"那...就吃{selected_nickname}（{user_id}）吧！（坏笑")
    a = httpx.get("https://zj.v.api.aa1.cn/api/eats/", timeout=None, verify=False)
    if a.status_code != 200:
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"好像没有访问成功...？[HTTP {a.status_code}]")
    a = a.json()
    if a['code'] != 200:
        msg = a['msg']
        code = a['code']
        await matcher.finish(MessageSegment.reply(event.message_id) + f"好像没有获取到QAQ...{msg}[{code}]")
    random_number = rd.randint(1, 2)
    select = a[f'meal{random_number}']
    await matcher.finish(MessageSegment.reply(event.message_id) + f"{a['mealwhat']}\n要不{select}吧！")


@nc_version_info.handle()
async def _version_info(bot: Bot, matcher: Matcher, event: MessageEvent):
    if "凌辉" not in str(MessageEvent.raw_message):
        await matcher.finish()
    data = await bot.get_version_info()
    await matcher.finish(MessageSegment.reply(event.message_id) + f"当前使用的客户端实例：{data["app_name"]}\n"
                                                                  f"客户端实例版本号：{data['app_version']}\n"
                                                                  f"子模块版本号：{data['protocol_version']}\n")
