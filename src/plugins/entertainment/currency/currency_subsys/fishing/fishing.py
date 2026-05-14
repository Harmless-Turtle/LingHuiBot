from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment,Bot
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import get_session, async_scoped_session

from .items import *
from .models import process_fishing
from ...models import get_mohui_data
from ....commands import fishing_downswing, buy_fishing_hook,fishing_hook_attribute
from .....utils import handle_errors,batch_get


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
    fishing_sql = await process_fishing(session=get_session(), user_id=user_id)
    if fishing_sql:
        await matcher.finish(MessageSegment.reply(event.message_id) + fishing_sql)
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
    user_coin = await get_mohui_data(session=session, user_id=str(event.user_id))
    hook_data = {}
    hook_name = FishingHook.all_hook_names
    if args not in hook_name:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"请输入正确的鱼钩名称，目前有：{', '.join(FishingHook.all_hook_names)}\n鱼钩的详细参数，请使用命令“鱼钩属性”获取")
    for item in FishingHook.hook_attribute:
        if item['name'] in args:
            hook_data = item
            break
    if user_coin.mohui_coin < hook_data['price']:
        await matcher.finish(MessageSegment.reply(event.message_id)+"你的墨辉币似乎不足以购买这个鱼钩qwq")
    #TODO 2026.5.14 22：27归档：钓鱼系统的购买鱼钩功能尚未完善。

@fishing_hook_attribute.handle()
@handle_errors
async def _fishing_hook_attribute(
        bot:Bot,
        matcher: Matcher,
        event: GroupMessageEvent,
        args: Message = CommandArg(),
):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    final_list = []
    for item in FishingHook.hook_attribute:
        level,name,price,durability,bonus = item['level'],item['name'],item['price'],item["durability"],item["bonus"]
        text = (
            f"鱼钩等级：{level}\n"
            f"鱼钩名称：{name}\n"
            f"价格：{price}墨辉币\n"
            f"耐久：{durability}\n"
            f"珍惜品种加权：{bonus}"
        )
        make_text = await batch_get(text, None, event.self_id, f"{event.self_id}")
        final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)