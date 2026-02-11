import random as rd
import re
import time
from datetime import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import httpx
import requests
from nonebot import logger, on_request, on_notice, get_driver
# 导入事件响应器以进行操作
from nonebot.adapters.onebot.v11 import (
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
    PrivateMessageEvent,
    FriendRequestEvent,
    GroupMessageEvent,
    GroupRequestEvent,
    PokeNotifyEvent,
    MessageSegment,
    MessageEvent,
    NoticeEvent,
    Message,
    Event,
    Bot,
)
# 导入异常基类MatcherException，以限制try-except捕获正常finish函数抛出的异常
from nonebot.exception import ActionFailed
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command,on_type
from nonebot.rule import to_me, is_type, Rule

from src.plugins import utils

# 定义Data存放路径并作为全局变量使用
path = Path.cwd() / 'data' / 'Main'
Poke_Path = path / "Poke_Text.json"
Welcome_Path = path / "Welcome_System.json"
AWord_Path = path / "AWord.json"
Sign_in_Path = path / "Sign_in" / "Sign_in.json"
Sign_in_Pic_True = path / "Sign_in" / "Background_True.png"
Sign_in_Pic_False = path / "Sign_in" / "Background_False.jpg"
black_list_path = path / "black_list.json"
# 校验文件
utils.ensure_files_exist(
    file_path=[
        Poke_Path,
        Welcome_Path,
        AWord_Path,
        Sign_in_Path,
        Sign_in_Pic_True,
        Sign_in_Pic_False,
        black_list_path
    ],
    description="main"
)

# 获取机器人的名字
config = get_driver().config
try:
    nickname = config.nickname
    logger.info("加载完成")
except AttributeError:
    logger.warning("未加载到NICKNAME配置，请前往dotEnv文件新建该配置项，否则部分功能可能不可用")


async def check_bt(event: GroupMessageEvent):
    s = re.match(r'我是(.+)控', str(event.original_message))
    if s:
        return True
    else:
        return False


async def chek_add_welcome(event: GroupIncreaseNoticeEvent):
    welcome_data = utils.handle_json(Welcome_Path, 'r')
    group_id = event.group_id
    logger.info(f"检查群 {group_id} 的欢迎配置，当前数据：{welcome_data.get(group_id)}")
    if welcome_data.get(group_id, False):
        welcome_settings = welcome_data[group_id]
        logger.info(f"群 {group_id} 的欢迎模式为：{welcome_settings.get('mode')}")
        return welcome_settings.get('mode')
    return False


async def chek_group_member_change(event: GroupDecreaseNoticeEvent):
    try:
        data = utils.handle_json(path / "GroupMemberChange.json", "r")
        logger.info(f"检查群 {event.group_id} 的退群通知开关，当前状态：{data.get(str(event.group_id))}")
        return data.get(str(event.group_id), False)
    except Exception as e:
        logger.error(f"读取退群通知配置失败：{e}")
        return False


async def add_group_switch(event: GroupRequestEvent):
    group_switch_data = utils.handle_json(path / "add_group_switch.json", "r")
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


# 基础功能
sign_in = on_command("签到", aliases={"好久不见"}, priority=2, block=True)
poke_check = on_type(PokeNotifyEvent,to_me())
tarot = on_command("塔罗牌", priority=4, block=True)
a_word = on_command("一言", priority=4, block=True)
btfrk = on_command("我是", rule=check_bt)
like = on_command("点赞", aliases={"赞我"}, block=True)
eat_what = on_command("今天吃什么")

# 入群检查
add_group = on_request(rule=add_group_switch)
switch_add_group = on_command("入群检测", permission=SUPERUSER, block=True)
# 入群欢迎系统
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
# 被点赞事件监测
Like_Friend = on_notice(rule=is_type(NoticeEvent) & chek_friend_like)
# 加好友事件请求
Add_Friend = on_request(rule=is_type(FriendRequestEvent), priority=1, block=True)
# 处理是否同意加好友
Choice_Friend = on_command("同意", rule=chek_friend, permission=SUPERUSER, aliases={"拒绝"}, block=True)

handle_group = on_command("允许加群", aliases={"拒绝加群"}, block=True)

Add_Welcome = on_notice(rule=is_type(GroupIncreaseNoticeEvent) & Rule(chek_add_welcome), priority=1, block=True)

# 定义全局变量
Poke_Count = 0
Time_Count = time.time()
Send = True
AT_count = 0
AT_Time = time.time()


@poke_check.handle()
@utils.handle_errors
async def pc_function(matcher: Matcher):
    global Poke_Count, Time_Count, Send
    if Poke_Count >= 3 and time.time() - Time_Count <= 120:
        if time.time() - Time_Count >= 120:
            Poke_Count = 0
            pc_function()
        else:
            if Send:
                Send = False
                await matcher.finish("呜呜...不可以再捏了~（2分钟后可以继续捏~）")
            else:
                pass
    else:
        Send = True
        text_list = utils.handle_json(Poke_Path, 'r')

        Poke_Count += 1
        Time_Count = time.time()
        random_message = text_list[rd.randint(0, len(text_list) - 1)]
        await matcher.finish(f"{random_message}")


@tarot.handle()
@utils.handle_errors
async def tarot_function(matcher: Matcher, event: MessageEvent):
    get = requests.get("https://oiapi.net/API/Tarot").json()
    if get['code'] != 1:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"遇到错误：{get['message']}[{get['code']}]")
    data = get['data']
    send = data[rd.randint(0, len(data) - 1)]
    meaning = send['meaning']
    name_cn = send['name_cn']
    position = send['type']
    position_meaning = send[f"{position}"]
    pic_a_url = send['pic']
    await matcher.finish(
        MessageSegment.reply(event.message_id) + MessageSegment.image(pic_a_url) + f"""你抽到了{name_cn}
这张牌的意思是：{meaning}，方位是{position}
这个牌的方位解释为：{position_meaning}""")


@Add_Welcome.handle()
@utils.handle_errors
async def welcome(matcher: Matcher, event=GroupIncreaseNoticeEvent):
    if event.user_id == event.self_id: await matcher.finish()
    welcome_dict = utils.handle_json(Welcome_Path, 'r')
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


SelfJoinGroupWelcome = on_notice(rule=is_type(GroupIncreaseNoticeEvent), priority=1, block=True)


@SelfJoinGroupWelcome.handle()
@utils.handle_errors
async def self_join_group_welcome_function(matcher: Matcher, event=GroupIncreaseNoticeEvent):
    if event.user_id == event.self_id:
        await matcher.finish(
            "嗷呜~感谢您使用凌辉Bot~我可以给你提供Furry的相关功能，以及一些其他的功能哦~\n"
            "如果您想要了解更多功能，请输入“菜单”来获取帮助信息哦~\n"
            "如果您担心与群里其他Bot的命令冲突，可以通过“凌辉菜单”来使用菜单哦www~希望您能喜欢我~\n"
            "如果您有任何问题，请随时联系管理员[1097740481]哦~")
    else:
        pass


@change_welcome.handle()
@utils.handle_errors
async def change_welcome_function(matcher: Matcher, event: GroupMessageEvent):
    welcome_config = utils.handle_json(Welcome_Path, 'r')
    group_id = str(event.group_id)
    args = event.get_message()
    if "开" in str(args):
        welcome_config[group_id] = {"mode": None, "Text": None}
        welcome_config[group_id]['mode'] = True
        if not welcome_config[group_id].get('Text', False):
            welcome_config[group_id][
                'Text'] = "新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~"
    elif "关" in str(args):
        if not welcome_config.get(group_id, False):
            await matcher.finish(MessageSegment.reply(
                event.message_id) + "本群似乎还没有创建过入群欢迎的任务，请先通过“入群欢迎开”的命令来创建哦w")
        welcome_config[group_id]["mode"] = False
    else:
        mode = None
        text = "未启动"
        if welcome_config.get(f"{group_id}", False):
            mode = welcome_config[group_id]["mode"]
            if not welcome_config[group_id].get('Text', False):
                text = "新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~"
            else:
                text = welcome_config[group_id]['Text']
        mode_text = "关闭"
        if mode:
            mode_text = "开启"
        elif mode is None:
            mode_text = "未启动"
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"当前群聊的入群欢迎状态为：{mode_text}\n新人入群欢迎文本：{text}")
    utils.handle_json(Welcome_Path, 'w', welcome_config)
    await matcher.finish(MessageSegment.reply(event.message_id) + "操作成功完成。")


@change_welcome_text.handle()
@utils.handle_errors
async def cwt_function(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = str(args)
    welcome_data = utils.handle_json(Welcome_Path, 'r')
    group = str(event.group_id)
    text = ""
    if not welcome_data.get(group, False):
        text = "由于未创建入群欢迎任务，所以本次操作将自动打开本群的入群欢迎提示~\n"
    new_dict = {
        f"{group}": {
            "mode": True,
            "Text": args
        }
    }
    welcome_data.update(new_dict)
    text_1 = "入群文本已经成功替换啦~"
    if args == "":
        welcome_data[group][
            'Text'] = "新人记得给群主早上请安晚上侍寝（bushi\n欢迎新成员加入本群！凌辉Bot欢迎您~\nWelcome new members to join this family! Linghui Bot welcomes you~"
        text_1 = "由于未找到对应的文本，所以本次操作将会使用默认文本来进行入群欢迎~"
    utils.handle_json(Welcome_Path, 'w', welcome_data)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"{text}{text_1}")


@a_word.handle()
@utils.handle_errors
async def a_word_function(matcher: Matcher, event=MessageEvent, args: Message = CommandArg()):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    word_list = utils.handle_json(AWord_Path, 'r')

    result = word_list[rd.randint(0, len(word_list) - 1)]
    await matcher.finish(MessageSegment.reply(event.message_id) + f"“{result}”")


# 签到触发器与实现
@sign_in.handle()
@utils.handle_errors
async def sign_in_function(matcher: Matcher, event: GroupMessageEvent,
                           args: Message = CommandArg()):
    if args.extract_plain_text():
        await matcher.finish()  # 若消息后面存在文本则不响应
    full = str(event.original_message).strip()
    if any(name not in full for name in nickname):
        await matcher.finish()
    # 打开文件并写入Sign_Dict字典
    sign_dict = utils.handle_json(Sign_in_Path, 'r')
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
    utils.handle_json(Sign_in_Path, 'w', sign_dict)
    a_word_list = utils.handle_json(AWord_Path, 'r')
    result = a_word_list[rd.randint(0, len(a_word_list) - 1)]
    # 判断：调用是否出现“好久不见”字样
    if "好久不见" in str(event.message):
        # 生成检测到“好久不见”字样的默认值
        text = "诶...好像也没有太久吧~是不是记错时间了呀~\n"
        pic = Sign_in_Pic_False
        # 判断：如果读取用户的格林威治时间戳减去当前时间戳大于或等于259200秒（即3天整），则更改输出条件。
        if (greenwich_time - user_greenwich_time) >= 259200:
            text = "确实好久不见了诶~抱抱~\n"
            pic = Sign_in_Pic_True
        # 输出
        await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.image(
            pic) + f"{text}签到成功。本月在本群中已签到{user_count}次，今天在本群中排名第{group_count}位~\n"
                   f"——————\n"
                   f"“{result}”")
    # 输出
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"{text}签到成功。您本月在本群中已签到{user_count}次，今天在本群中排名第{group_count}位。\n"
                            f"——————\n"
                            f"“{result}”")


@btfrk.handle()
@utils.handle_errors
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


@exit_change.handle()
@utils.handle_errors
async def change_exit_function(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = str(args)
    data = utils.handle_json(path / "GroupMemberChange.json", "r")
    exit_message, write = "", None
    if "开" in args:
        write = True
        exit_status = "打开"
        exit_message = "当有人退群时会发出消息提示哦~"
    elif "关" in args:
        write = False
        exit_status = "关闭"
    else:
        text = "本群的退群通知是关闭状态捏"
        if data.get(f"{event.group_id}", False):
            if data[f'{event.group_id}']:
                text = "本群的退群通知是打开状态捏"
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"{text}~\n输入“退群提示关”或“退群提示开”来更改功能开关")
        return

    logger.info(args)
    data[f'{event.group_id}'] = write
    utils.handle_json(path / "GroupMemberChange.json", "w", data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"好~凌辉Bot已经{exit_status}了本群的退群提示w~{exit_message}")


@GroupExitMember.handle()
@utils.handle_errors
async def handle_group_decrease(event: GroupDecreaseNoticeEvent, bot: Bot, matcher: Matcher):
    logger.info(f"触发退群事件：{event.group_id}")
    # 处理 Bot 自己被踢的情况
    if event.sub_type == "kick_me":
        await bot.send_private_msg(
            user_id=1097740481,
            message=f"⚠️ Bot被踢出群聊！\n"
                    f"时间：{dt.fromtimestamp(event.time).strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"群号：{event.group_id}"
        )
        await matcher.finish()
    # 获取用户信息

    try:
        user_info = await bot.get_stranger_info(user_id=event.user_id)
        user_nickname = user_info.get("nickname", "未知用户")
    except ActionFailed:
        user_nickname = "信息获取失败"

    # 处理退群原因
    if event.sub_type == "kick":
        operator_id = getattr(event, "operator_id", 0)
        if operator_id > 0:
            # 尝试获取操作者信息
            try:
                operator_info = await bot.get_group_member_info(
                    group_id=event.group_id,
                    user_id=operator_id
                )
                operator_name = operator_info.get("nickname", str(operator_id))
            except ActionFailed:
                operator_name = str(operator_id)
            reason = f"被管理员 {operator_name} 移出"
        else:
            reason = "被管理员移出"  # 无权限时的通用描述
    elif event.sub_type == "leave":
        reason = "主动退群"
    else:
        reason = "未知原因"

    # 构造消息
    message = Message(
        f"似乎有人离开了我们...？"
        f"时间：{dt.fromtimestamp(event.time).strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"用户：{user_nickname} ({event.user_id})\n"
        f"原因：{reason}"
    )

    # 发送到群聊
    await bot.send_group_msg(
        group_id=event.group_id,
        message=message
    )


@Like_Friend.handle()
@utils.handle_errors
async def lf_function(matcher: Matcher, event: NoticeEvent):
    from nonebot import get_bot
    bot = get_bot()
    data = event.model_dump()
    user_data = utils.handle_json(path / "Friend_Like.json", 'r')
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
    utils.handle_json(path / "Friend_Like.json", 'w', user_data)
    try:
        if user_id != 1097740481:
            await bot.send_private_msg(user_id=user_id, message=text)
            logger.info("已经回赞完毕")
    except ActionFailed:
        logger.error(f"发送点赞消息失败，可能是因为没有添加好友")


@Add_Friend.handle()
@utils.handle_errors
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


@Choice_Friend.handle()
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


@add_group.handle()
@utils.handle_errors
async def handle_add_group(matcher: Matcher, bot: Bot, event: GroupRequestEvent):
    user = await bot.get_stranger_info(user_id=event.user_id)
    user = user["nick"]
    comment = event.comment
    if comment == "":
        comment = "未填写入群理由"
    ban_text = "死全家滚开去死废渣傻逼脑残智障败贱货垃圾杂种操你妈"
    if comment in ban_text:
        await bot.set_group_add_request(
            flag=str(event.flag),
            approve=False,
            sub_type="add",
            reason="你的申请存在违禁词库中,请修改后重新申请。"
        )
        await matcher.finish(
            f"似乎有人想要加入我们awa...\n"
            f"请求类型：{event.request_type}\n"
            f"子类型：{event.sub_type}\n"
            f"申请人信息：{user}[{event.user_id}]\n"
            f"进群理由:\n"
            f"（思考）...？似乎在凌辉的内置禁止词库中？\n"
            f"⚠️已满足判决条件；自动处理生效，将主动拒绝此入群消息！\n"
            f"如果要手动同意，请关闭入群审核功能后让用户重新申请。"
        )
    await matcher.finish(
        f"似乎有人想要加入我们awa...\n"
        f"请求类型：{event.request_type}\n"
        f"子类型：{event.sub_type}\n"
        f"申请人信息：{user}[{event.user_id}]\n"
        f"进群理由:{event.comment}\n"
        f"要同意此人入群嘛awa？\n"
        f"可以通过“允许加群{event.flag}”或“拒绝加群{event.flag}”来处理此请求（请在Bot为群管理员时进行操作~"
    )


@switch_add_group.handle()
async def utils_switch_add_group(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    arg = args.extract_plain_text()

    data = utils.handle_json(path / "add_group_switch.json", 'r')
    if arg == "开":
        write = True
        feature_status = "打开"
    elif arg == "关":
        write = False
        feature_status = "关闭"
    else:
        text = "当前Bot的入群检测状态为：关闭"
        if data.get(str(event.group_id), False):
            if data[str(event.group_id)]:
                text = "当前Bot的入群检测状态为：开启"
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"{text}~\n"
            f"输入“入群检测开”或“入群检测关”来更改功能开关"
        )
        return

    data[str(event.group_id)] = write
    utils.handle_json(path / "add_group_switch.json", 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"好~凌辉Bot已经{feature_status}了本群的入群检测功能w~"
    )


@handle_group.handle()
async def handle_add_group(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    user = await bot.get_group_member_info(group_id=event.group_id, user_id=event.self_id)
    logger.info(user)
    if user['role'] == 'member':
        await matcher.finish(MessageSegment.reply(event.message_id) + "请先将Bot设置为管理员哦~")
    if "允许" in str(event.get_message):
        select = True
    elif "拒绝" in str(event.get_message):
        select = False
    else:
        await matcher.finish(MessageSegment.reply(event.message_id) + "命令不正确")
        return
    try:
        await bot.set_group_add_request(
            flag=str(args),
            sub_type="add",
            approve=select,
            reason="管理员拒绝通过。"
        )
        await matcher.finish(MessageSegment.reply(event.message_id) + "已经处理了此请求。")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到对应的flag，请检查flag是否正确。")


@event_preprocessor
def black_processor(event:Event):
    user_id = event.user_id
    superusers = get_driver().config.superusers
    if event.post_type=='notice':
        return
    if(uid := str(vars(event).get('user_id',None))) in superusers:
        return
    black_list = utils.handle_json(black_list_path, 'r')