from datetime import datetime as dt

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    GroupDecreaseNoticeEvent,
    GroupMessageEvent,
    GroupRequestEvent,
    MessageSegment,
    Message,
    Bot
)
from nonebot.exception import ActionFailed
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from src.plugins.main.check_file import (
    group_join_flag_path,
    check_group_member_path,
    welcome_path,
    add_group_check_path,
)
from src.plugins.main.commands import (
    change_welcome_text,
    GroupExitMember,
    change_welcome,
    switch_add_group,
    exit_change,
    handle_group,
    add_group,
)
from src.plugins.utils import handle_errors, handle_json


@GroupExitMember.handle()
@handle_errors
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


@exit_change.handle()
@handle_errors
async def change_exit_function(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = str(args)
    data = handle_json(check_group_member_path, "r")
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
    handle_json(check_group_member_path, "w", data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"好~凌辉Bot已经{exit_status}了本群的退群提示w~{exit_message}")


@change_welcome_text.handle()
@handle_errors
async def cwt_function(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    args = str(args)
    welcome_data = handle_json(welcome_path, 'r')
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
    handle_json(welcome_path, 'w', welcome_data)
    await matcher.finish(MessageSegment.reply(event.message_id) + f"{text}{text_1}")


@change_welcome.handle()
@handle_errors
async def change_welcome_function(matcher: Matcher, event: GroupMessageEvent):
    welcome_config = handle_json(welcome_path, 'r')
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
    handle_json(welcome_path, 'w', welcome_config)
    await matcher.finish(MessageSegment.reply(event.message_id) + "操作成功完成。")


@add_group.handle()
@handle_errors
async def handle_add_group(matcher: Matcher, bot: Bot, event: GroupRequestEvent):
    user = await bot.get_stranger_info(user_id=event.user_id)
    data = handle_json(group_join_flag_path, 'r')
    if not data.get(str(event.group_id), False):
        data[str(event.group_id)] = []
    data[str(event.group_id)].append(event.flag)
    handle_json(group_join_flag_path, 'w', data)
    user = user["nick"]
    comment = event.comment
    if comment is None or comment.strip() == "":
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
        f"可以通过“允许加群{len(data[str(event.group_id)])}”或“拒绝加群{len(data[str(event.group_id)])}”来处理此请求（请在Bot为群管理员时进行操作~"
    )


@switch_add_group.handle()
async def utils_switch_add_group(matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()):
    arg = args.extract_plain_text()

    data = handle_json(add_group_check_path, 'r')
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
    handle_json(add_group_check_path, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"好~凌辉Bot已经{feature_status}了本群的入群检测功能w~"
    )


@handle_group.handle()
async def handle_add_group(matcher: Matcher, event: GroupMessageEvent, bot: Bot, args: Message = CommandArg()):
    self_is_admin = await bot.get_group_member_info(group_id=event.group_id, user_id=event.self_id)
    if self_is_admin['role'] == 'member':
        await matcher.finish(MessageSegment.reply(event.message_id) + "请先将Bot设置为管理员哦~")
    user_is_admin = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    if user_is_admin['role'] == 'member':
        await matcher.finish(MessageSegment.reply(event.message_id) + "你不是群管理组，不允许进行这个操作呢qwq")
    if "允许" in str(event.get_message()):
        select = True
    elif "拒绝" in str(event.get_message()):
        select = False
    else:
        await matcher.finish(MessageSegment.reply(event.message_id) + "命令不正确")
        return
    flag_list = handle_json(group_join_flag_path, 'r')
    group_flag_list = flag_list[f"{event.group_id}"]
    if len(group_flag_list) == 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "这个群的待审列表是空的qwq")
    select_flag = 1
    try:
        select_flag = int(str(args))
    except ValueError:
        await matcher.finish(MessageSegment.reply(event.message_id) + "输入不正确。请确认输入了纯数字")
    select_flag = group_flag_list[select_flag - 1]
    del group_flag_list[int(str(args)) - 1]
    handle_json(group_join_flag_path, 'w', flag_list)
    try:
        await bot.set_group_add_request(
            flag=str(select_flag),
            sub_type="add",
            approve=select,
            reason="管理员拒绝通过。"
        )
        await matcher.finish(MessageSegment.reply(event.message_id) + "已经处理了此请求。")
    except ActionFailed:
        await matcher.finish(MessageSegment.reply(event.message_id) + "未找到对应的flag，请检查flag是否正确。")
