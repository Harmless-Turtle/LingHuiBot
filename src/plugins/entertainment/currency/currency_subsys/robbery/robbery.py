import random as rd
import time

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment, Message
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from src.plugins.entertainment.check_files import robbery_time_path
from src.plugins.entertainment.commands import (
    robbery
)
from src.plugins.entertainment.currency.models import (
    get_user_coin,
    modify_user_coin,
)
from src.plugins.utils import handle_errors, at_is_true, handle_json


@robbery.handle()
@handle_errors
async def _robbery(
        bot: Bot,
        matcher: Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    target_id = await  at_is_true(event, args)
    # 判断是否为全体成员
    if target_id == "all":
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "呃...你是要打劫全部人吗（"
        )
    elif target_id == f"{event.user_id}":
        await matcher.finish(MessageSegment.reply(event.message_id) + "你为什么要打劫自己（歪头")
    elif target_id == f"{event.self_id}":
        await matcher.finish(MessageSegment.reply(event.message_id) + "打劫机器人干什么QAQ...")
    elif target_id == "finish":
        await matcher.finish()
    elif target_id == "illegal":
        await matcher.finish(MessageSegment.reply(event.message_id) + "请输入正确的用户ID或者at对象捏")
    # 初始化数据
    count = 0
    now_time = int(time.time())
    time_data = handle_json(robbery_time_path, 'r')
    # 尝试获取用户状态
    user_data = time_data.get(str(event.user_id), {})
    # 如果用户状态存在，则进入判断
    if user_data:
        # 获取计数器
        count = user_data['count']
        if count >= 5:
            if user_data['disturb']:
                time_data[f'{event.user_id}']['disturb'] = False
                handle_json(robbery_time_path, 'w', time_data)
                await matcher.finish(MessageSegment.reply(
                    event.message_id) + "你今天已经抢太多次啦，休息一下吧uwu\n此消息仅会发送1次，直至时间足够刷新。")
            await matcher.finish()
        # 统一判断并删除
        if now_time - user_data['time'] >= 86400:
            del time_data[str(event.user_id)]
    # 获取被打劫对象的墨辉币数量以及昵称信息
    coin_obj = await get_user_coin(session, str(target_id))
    stranger_info = await bot.get_stranger_info(user_id=int(target_id))
    nickname_obj = stranger_info.get('nickname', '来自远方的旅人')
    # 随机数用以判断是否打劫成功
    correct = rd.randint(1, 5)
    # 获取本次打劫的墨辉币数量
    operate_coins = rd.randint(100, 500)
    # 获取自己和对方的墨辉币数量
    coin_self = await get_user_coin(session, str(event.user_id))
    # 如果自己或者对方的墨辉币数量不足以扣除，则直接不处理。
    if operate_coins >= coin_obj:
        await matcher.finish(MessageSegment.reply(event.message_id) + "对方的墨辉币似乎不够你打劫的awa")
    elif operate_coins >= coin_self:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你的墨辉币似乎不够你打劫的awa")
    # 创建用户计数器并写入json文件
    count += 1
    time_data[str(event.user_id)] = {
        "time": int(time.time()),
        "count": count,
        "disturb": True
    }
    handle_json(robbery_time_path, 'w', time_data)
    # 判断是否打劫成功
    if correct == 2:
        await modify_user_coin(session, str(event.user_id), -operate_coins)
        await modify_user_coin(session, str(target_id), operate_coins)
        coin_self = await get_user_coin(session, str(event.user_id))
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"打劫失败了...你还被{nickname_obj}劫走了{operate_coins}个墨辉币！\n"
                                f"你现在还有{coin_self}个墨辉币uwu")
    await modify_user_coin(session, str(event.user_id), operate_coins)
    await modify_user_coin(session, str(target_id), -operate_coins)
    await matcher.finish(
        MessageSegment.reply(event.message_id) + f"打劫成功了捏~你打劫了“{nickname_obj}” {operate_coins}个墨辉币捏")
