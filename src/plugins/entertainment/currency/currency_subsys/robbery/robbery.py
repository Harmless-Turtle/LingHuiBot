import random as rd
import time

from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session

from ...exceptions import CurrencyError
from ...models import get_mohui_data, add_mohui_coin, remove_mohui_coin
from ....check_files import robbery_time_path
from ....commands import robbery
from .....utils import handle_errors, handle_json


@robbery.handle()
@handle_errors
async def _robbery(
        bot: Bot,
        matcher: Matcher,
        session: async_scoped_session,
        event: GroupMessageEvent
):
    try:
        msg = event.original_message
        if not 2 <= len(msg) <= 3:
            raise CurrencyError("参数格式错误！格式：抢劫@<一个用户>")

        at_seg = msg[1]
        if not at_seg.type == "at":
            raise CurrencyError("请输入正确的用户ID或者at对象捏")

        target_id = str(at_seg.data.get("qq"))
        if target_id == str(event.user_id):
            raise CurrencyError("你为什么要打劫自己（歪头")
        elif target_id == str(event.self_id):
            raise CurrencyError("打劫机器人干什么QAQ...")
        elif target_id == "all":
            raise CurrencyError("呃...你是要打劫全部人吗（")
    except CurrencyError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    # 随机生成本次打劫的墨辉币数量
    operate_coins = rd.randint(100, 500)
    # 获取目标方的昵称
    stranger_info = await bot.get_stranger_info(user_id=int(target_id))
    nickname = stranger_info.get('nickname', '来自远方的旅人')

    try:
        await _process_robbery(
            matcher,
            event,
            session,
            target_id,
            operate_coins,
            nickname
        )
    except CurrencyError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
        return

    await matcher.finish(
        MessageSegment.reply(event.message_id) +
        f"打劫成功了捏~你打劫了“{nickname}” {operate_coins}个墨辉币捏"
    )


async def _process_robbery(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        target_id: str,
        operate_coins: int,
        nickname: str
):
    # 生成随机数用以判断是否打劫成功
    correct = rd.randint(1, 5)

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
                raise CurrencyError(
                    "你今天已经抢太多次啦，休息一下吧uwu\n"
                    "此消息仅会发送1次，直至时间足够刷新。"
                )
        # 统一判断并删除
        if now_time - user_data['time'] >= 86400:
            del time_data[str(event.user_id)]

    # 获取双方的墨辉币数量
    from_user_data = await get_mohui_data(session, str(event.user_id))
    from_user_coins = from_user_data.mohui_coin
    target_user_data = await get_mohui_data(session, str(target_id))
    target_user_coins = target_user_data.mohui_coin

    # 如果自己或者对方的墨辉币数量不足以扣除，则raise。
    if operate_coins >= target_user_coins:
        raise CurrencyError("对方的墨辉币似乎不够你打劫的awa")
    if operate_coins >= from_user_coins:
        raise CurrencyError("你的墨辉币似乎不够你打劫的awa")

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
        await remove_mohui_coin(session, str(event.user_id), operate_coins)
        await add_mohui_coin(session, str(target_id), operate_coins)
        obj2 = await get_mohui_data(session, str(event.user_id))
        from_user_coins = obj2.mohui_coin

        await matcher.finish(
            MessageSegment.reply(event.message_id) +
            f"打劫失败了...你还被{nickname}劫走了{operate_coins}个墨辉币！\n"
            f"你现在还有{from_user_coins}个墨辉币uwu"
        )
    await add_mohui_coin(session, str(event.user_id), operate_coins)
    await remove_mohui_coin(session, str(target_id), operate_coins)
