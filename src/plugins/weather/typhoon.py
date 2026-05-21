from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment,Message
from nonebot.exception import FinishedException
from nonebot.internal.matcher import Matcher
from typing import Annotated
from nonebot.params import Depends
from nonebot_plugin_orm import AsyncSession

from src.plugins.utils import handle_errors
from .commands import typhoon_check,typhoon_subscribe
from .utils import get_typhoon_card_image
from .models import TyphoonSubscribe, add_typhoon_sub
from ..utils import handle_json
from .check_file import typhoon_id_path

@typhoon_check.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
):
    try:
        # 直接调用复用方法
        img_bytes = await get_typhoon_card_image()
        await matcher.finish(MessageSegment.image(img_bytes))
    except FinishedException:
        pass
    except Exception as e:
        # 统一处理业务层抛上来的异常
        await matcher.finish(MessageSegment.reply(event.message_id) + f"获取台风卡片失败，原因: {e}")


@typhoon_subscribe.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: AsyncSession,
):
    # 直接调用函数获取配置
    group_settings = await add_typhoon_sub(session, event.group_id)

    # 在修改前先读取当前状态
    current_enable = group_settings.enable

    # 切换状态
    new_enable = not current_enable
    group_settings.enable = new_enable
    await session.commit()

    # 使用局部变量，不要在 commit 后访问对象属性
    text = ""
    if new_enable:
        try:
            data = handle_json(typhoon_id_path, "r")
            if data and 'last_pushed_id' in data:
                text = f"\n当前的最新台风id为：{data['last_pushed_id']}"
        except Exception:
            pass
        reply_msg = f"已经在本群订阅了台风动态，在新的台风到来之前将会在群里发送消息捏awa{text}"
    else:
        reply_msg = "已取消本群的台风动态订阅"

    await matcher.finish(MessageSegment.reply(event.message_id) + reply_msg)