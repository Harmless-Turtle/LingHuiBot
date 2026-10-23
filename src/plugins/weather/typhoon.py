from nonebot import get_bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot_plugin_orm import async_scoped_session

from ..utils import batch_get, handle_errors
from .commands import typhoon_check, typhoon_subscribe
from .utils import get_current_typhoon_cards
from .models import add_typhoon_sub


@typhoon_check.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
):
    card_images = await get_current_typhoon_cards()

    if not card_images:
        await matcher.finish("当前未获取到有效的台风数据信息捏 QAQ")

    if len(card_images) == 1:
        await matcher.finish(MessageSegment.image(card_images[0]))
    else:
        # 多台风共存：获取 bot 实例，并按照标准形式构造节点发包
        bot = get_bot()
        # 🌟 修正：遵循列表推导式 await batch_get 的解包逻辑
        picture_list = [await batch_get("", img, 3806419216, "凌辉Bot 台风查询") for img in card_images]
        # 🌟 修正：通过原生的 call_api 完成最终的合并发送
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=picture_list, time_noend=True)
        await matcher.finish()


@typhoon_subscribe.handle()
@handle_errors
async def _(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
):
    group_settings = await add_typhoon_sub(session, event.group_id)
    current_enable = group_settings.enable

    new_enable = not current_enable
    group_settings.enable = new_enable
    await session.commit()

    if new_enable:
        reply_msg = "已经在本群订阅了台风动态！现在开始，活跃中的台风将在每早 7 时准时为您推送实时全景简报，停编时也会发送最后一次收尾总结通知哦 awa"
    else:
        reply_msg = "已取消本群的台风动态订阅"

    await matcher.finish(MessageSegment.reply(event.message_id) + reply_msg)