from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment,Bot
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import get_session, async_scoped_session

from .items import *
from .models import (
    process_fishing,
    equip_hook,
    equip_rod,
    get_hook,
    get_rod
)
from ...models import get_mohui_data,remove_mohui_coin
from ....commands import (
    fishing_downswing,
    buy_fishing_hook,
    buy_fishing_rod,
    buy_fishing_bait,
    fishing_hook_attribute,
)
from .....utils import handle_errors,batch_get


@buy_fishing_rod.handle()
@handle_errors
async def _buy_fishing_rod(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
):
    args = args.extract_plain_text()
    user_coin = await get_mohui_data(session=session, user_id=str(event.user_id))
    user_rod = await get_rod(session=session, user_id=str(event.user_id))
    rod_data = {}
    rod_name = FishingRod.all_rod_names
    if args not in rod_name:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"请输入正确的鱼竿名称，目前有：{', '.join(FishingRod.all_rod_names)}\n鱼竿的详细参数，请使用命令“鱼竿属性”获取")
    for item in FishingRod.rod_attribute:
        if item['name'] in args:
            rod_data = item
            break
    if user_coin.mohui_coin < rod_data['price']:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你的墨辉币似乎不足以购买这个鱼竿qwq")
    if user_rod:
        buy_rod = {}
        for item in FishingRod.rod_attribute:
            if item['name'] in args:
                buy_rod = item
                break
        if rod_data['level'] <= buy_rod['level']:
            await matcher.finish(MessageSegment.reply(event.message_id) + f"你已经拥有了{user_rod}，不能降级购买或者购买同级鱼竿捏")
    await remove_mohui_coin(session=session, user_id=str(event.user_id), amount=rod_data['price'])
    await equip_rod(session=session, user_id=str(event.user_id),rod_key=rod_data['name'])
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"购买{rod_data['name']}成功！钓到鱼后允许起竿时间范围为{rod_data['bonus_min']}s~{rod_data['bonus_max']}s。")


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
    async with get_session() as session:
        fishing_sql = await process_fishing(session=session, user_id=user_id)
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
    # 获取想要购买的鱼钩的名称
    args = args.extract_plain_text()
    # 建立session会话，与SQL通信
    user_coin = await get_mohui_data(session=session, user_id=str(event.user_id))
    user_hook = await get_hook(session=session, user_id=str(event.user_id))
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
    text_temp = ''
    if user_hook:
        text_temp = "您已经购买过鱼钩了，本次购买将覆盖掉旧的鱼钩捏\n"
    await remove_mohui_coin(session=session, user_id=str(event.user_id), amount=hook_data['price'])
    await equip_hook(session=session, user_id=str(event.user_id), hook_key=hook_data['name'], durability=hook_data['durability'])
    await matcher.finish(MessageSegment.reply(event.message_id) + f"{text_temp}购买{hook_data['name']}成功！鱼钩耐久为{hook_data['durability']}，珍惜品种加权为{hook_data['bonus']}。")

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