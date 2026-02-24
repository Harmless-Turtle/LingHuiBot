import random as rd
import time

from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    Bot, GroupMessageEvent
)
from nonebot.matcher import Matcher

from .check_files import *
from .commands import *
from ..utils import handle_errors, handle_json



async def _marry_helper_func(bot:Bot,event:GroupMessageEvent,matcher:Matcher,is_switch:bool) -> None:
    # 获取必要数据
    user_member_list = await bot.call_api("get_group_member_list", group_id=event.group_id)  # 群成员列表
    data = handle_json(marry_json_path, 'r')
    if not data.get(str(event.user_id), {}).get(str(event.group_id)) and is_switch:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你还没有老婆！先用“今日老婆”找一个叭！")
    # 排除不应该被选中的用户组
    exclude_ids = {event.user_id, event.self_id}
    # 如果用户已经在data里
    user_data = data.get(str(event.user_id), {})
    if user_data and user_data.get(str(event.group_id)) and not is_switch:
        object_qq = data[str(event.user_id)][str(event.group_id)].get('object_qq')
        stranger_info = await bot.get_stranger_info(user_id=object_qq)
        nickname = stranger_info.get('nickname', '昵称获取失败')
        await matcher.finish(
            MessageSegment.reply(event.message_id) + f"怎么？想始乱终弃吗？你的老婆是：{nickname}[{object_qq}]")
    # 初始化计数器
    count = 0
    text = ""
    # 获取用户计数器
    if user_data.get(f"{event.group_id}"):
        count = user_data[f'{event.group_id}'].get('count',0)
    # 如果时间已超过24小时，自动重置计数器
    user_group_data = data.get(str(event.user_id), {}).get(str(event.group_id), {})
    if int(time.time()) - user_group_data.get('time', 0) >= 86400:
        count = 0
    if count == 0:
        pass
    elif count == 1:
        pass
    elif count == 2 and is_switch:
        text = "渣男，再换就不给你老婆了！\n"
    elif count == 3 and is_switch:
        data[str(event.user_id)][str(event.group_id)]['count'] = 4
        handle_json(marry_json_path, 'w', data)
        old_object_qq = data[str(event.user_id)][str(event.group_id)].get('object_qq')
        del data[str(event.user_id)][f'{event.group_id}']['object_qq'], data[old_object_qq][f'{event.group_id}']['object_qq']
        await matcher.finish(MessageSegment.reply(event.message_id) + "这么贪心，没收你的老婆！")
    else:
        await matcher.finish()
    # 如果是换老婆命令，则删除用户数据，由于上面已经做了用户数据合法性校验，故此处不需要校验。
    if is_switch:
        old_object_qq = data[str(event.user_id)][str(event.group_id)].get('object_qq')
        if old_object_qq:
            exclude_ids.add(int(old_object_qq))
        del data[str(event.user_id)][f'{event.group_id}'],data[old_object_qq][f'{event.group_id}']
    member_list = [
        x['user_id']
        for x in user_member_list
        if not x['is_robot'] and x['user_id'] not in exclude_ids and str(x['user_id']) not in data.keys()
    ]
    if not member_list:
        await matcher.finish("群里好像没有可选的对象了qwq")
    object_qq = member_list[rd.randint(0, len(member_list) - 1)]
    # 获取随机到的对象QQ昵称
    stranger_info = await bot.get_stranger_info(user_id=object_qq)
    nickname = stranger_info.get('nickname', '昵称获取失败')
    # 构建json信息
    self_json = {"object_qq": f"{object_qq}", "count": count + 1,"time":int(time.time())}
    object_json = {"object_qq": f"{event.user_id}","time":int(time.time())}
    data.setdefault(f'{event.user_id}', {})
    data.setdefault(f'{object_qq}', {})
    data[f'{event.user_id}'][f'{event.group_id}'] = self_json
    data[f'{object_qq}'][f'{event.group_id}'] = object_json
    handle_json(marry_json_path, 'w', data)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"{text}你的今日老婆是{nickname}[{object_qq}]嗷~\n"
        + MessageSegment.image(f"https://q.qlogo.cn/headimg_dl?dst_uin={object_qq}&spec=640&img_type=jpg"))


@marry_random.handle()
@handle_errors
async def marry(matcher: Matcher,event:GroupMessageEvent,bot:Bot):
    is_switch = False
    if "换老婆" in str(event.get_message()):
        is_switch = True
    await _marry_helper_func(bot,event,matcher,is_switch)