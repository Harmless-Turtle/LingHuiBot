from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import get_session, async_scoped_session

from src.plugins.entertainment.commands import (
    fishing_downswing,
    buy_fishing_hook
)
from src.plugins.entertainment.currency.models import get_user_coin
from src.plugins.utils import handle_errors
from .items import *
from .models import (
    process_fishing
)


@fishing_downswing.handle()
@handle_errors
async def _fishing_downswing(
        matcher: Matcher,
        event: GroupMessageEvent,
        args: Message = CommandArg()
) -> None:
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    # 获取用户id
    user_id = str(event.user_id)
    fishing_SQL = await process_fishing(session=get_session(), user_id=user_id)
    if fishing_SQL:
        await matcher.finish(MessageSegment.reply(event.message_id) + fishing_SQL)
    await matcher.finish("这是一个测试文本，用来表示通过了钓鱼的前置准备条件。")


@buy_fishing_hook.handle()
@handle_errors
async def _buy_fishing_hook(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg(),
):
    args = args.extract_plain_text()
    user_coin = await get_user_coin(session=session, user_id=str(event.user_id))
    hook_name = FishingHook.all_hook['name']
    if args not in hook_name:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"请输入正确的鱼钩名称，目前有：{', '.join(FishingHook.all_hook['name'])}")
    await matcher.finish("debug")
