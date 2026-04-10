import random as rd

from nonebot.adapters.onebot.v11 import Bot,GroupMessageEvent, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session

from src.plugins.utils import handle_errors
from src.plugins.entertainment.commands import (
    robbery
)
from src.plugins.entertainment.currency.models import (
    get_user_coin,
    modify_user_coin,
)


@robbery.handle()
@handle_errors
async def _robbery(
        bot:Bot,
        matcher: Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent
):
    target_id = None
    # 获取at的用户
    for msg_seg in event.original_message:
        if msg_seg.type == 'at':
            target_id = msg_seg.data['qq']
            break
    # 检查是否存在 at
    if not target_id:
        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            "唔...没有获取到你要打劫的人xwx\n请不要复制别人的指令，一定要自己at呢"
        )

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
    # 获取被打劫对象的墨辉币数量以及昵称信息
    coin_obj = await get_user_coin(session, str(target_id))
    stranger_info = await bot.get_stranger_info(user_id=int(target_id))
    nickname_obj = stranger_info.get('nickname', '来自远方的旅人')
    # 随机数用以判断是否打劫成功
    correct = rd.randint(1,5)
    # 获取本次打劫的墨辉币数量
    operate_coins = rd.randint(100, 500)
    # 获取自己和对方的墨辉币数量
    coin_self = await get_user_coin(session, str(event.user_id))
    # 如果自己或者对方的墨辉币数量不足以扣除，则直接不处理。
    if operate_coins >= coin_obj:
        await matcher.finish(MessageSegment.reply(event.message_id) + "对方的墨辉币似乎不够你打劫的awa")
    elif operate_coins >= coin_self:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你的墨辉币似乎不够你打劫的awa")
    # 判断是否打劫成功
    if correct == 2:
        await modify_user_coin(session, str(event.user_id), -operate_coins)
        await modify_user_coin(session, str(target_id), operate_coins)
        coin_self = await get_user_coin(session, str(event.user_id))
        await matcher.finish(MessageSegment.reply(event.message_id)+f"打劫失败了...你还被{nickname_obj}劫走了{operate_coins}个墨辉币！\n"
                                                                    f"你现在还有{coin_self}个墨辉币uwu")
    await modify_user_coin(session, str(event.user_id), operate_coins)
    await modify_user_coin(session, str(target_id), -operate_coins)
    await matcher.finish(MessageSegment.reply(event.message_id)+f"打劫成功了捏~你打劫了“{nickname_obj}” {operate_coins}个墨辉币捏")