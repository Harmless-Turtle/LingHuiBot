import time
import random
from datetime import datetime,timedelta

from nonebot import require,logger
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
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
    get_rod,
    add_bait,
    consume_bait,
    try_start_fishing,
    reduce_hook_durability,
    get_state,
    get_fishing_data,
    end_fishing,
    set_pull_window
)
from ...models import get_mohui_data,remove_mohui_coin
from ....commands import (
    fishing_downswing,
    buy_fishing_hook,
    buy_fishing_rod,
    buy_fishing_bait,
    fishing_hook_attribute,
    fishing_rod_attribute,
    fishing_pull
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
            await matcher.finish(MessageSegment.reply(event.message_id) + f"你已经拥有了{buy_rod['name']}，不能降级购买或者购买同级鱼竿捏")
    await remove_mohui_coin(session=session, user_id=str(event.user_id), amount=rod_data['price'])
    await equip_rod(session=session, user_id=str(event.user_id),rod_key=rod_data['name'])
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"购买{rod_data['name']}成功！钓到鱼后允许起竿时间范围为{rod_data['bonus_min']}s~{rod_data['bonus_max']}s。")

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

@fishing_rod_attribute.handle()
@handle_errors
async def _fishing_rod_attribute(
        bot:Bot,
        matcher: Matcher,
        event: GroupMessageEvent,
        args: Message = CommandArg(),
):
    if args.extract_plain_text(): await matcher.finish()  # 若消息后面存在文本则不响应
    final_list = []
    for item in FishingRod.rod_attribute:
        level,name,price,bonus_min,bonus_max = item['level'],item['name'],item['price'],item["bonus_min"],item["bonus_max"]
        text = (
            f"鱼竿等级：{level}\n"
            f"鱼竿名称：{name}\n"
            f"价格：{price}墨辉币\n"
            f"允许的起竿时间：{bonus_min}s~{bonus_max}s"
        )
        make_text = await batch_get(text, None, event.self_id, f"{event.self_id}")
        final_list.append(make_text)
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=final_list, time_noend=True)


@buy_fishing_bait.handle()
@handle_errors
async def _buy_fishing_bait(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg(),
):
    bait_name = FishingBait.bait_names
    raw_args = args.extract_plain_text().strip().split()
    if not raw_args:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"请输入正确的饵料名称，目前有：{', '.join(bait_name)}。\n饵料的详细参数，请使用命令“饵料属性”获取")

    bait_target = raw_args[0]
    count = 1
    if len(raw_args) > 1:
        try:
            count = int(raw_args[1])
            if count <= 0:
                raise ValueError
            if count > 100:
                await matcher.finish(MessageSegment.reply(event.message_id) + "一次购买的数量不能超过100个哦qwq")
        except ValueError:
            await matcher.finish(MessageSegment.reply(event.message_id) + "购买数量必须是正整数呢awa")
    user_coin = await get_mohui_data(session=session, user_id=str(event.user_id))

    if bait_target not in bait_name:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"请输入正确的饵料名称，目前有：{', '.join(bait_name)}\n饵料的详细参数，请使用命令“饵料属性”获取")
    bait_data = {}
    for item in FishingBait.bait_attribute:
        if item['name'] == bait_target:
            bait_data = item
            break
    total_price = bait_data['price'] * count
    if user_coin.mohui_coin < total_price:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"你的墨辉币不足以购买 {count} 个 {bait_data['name']} qwq\n总共需要: {total_price} 墨辉币，当前剩余: {user_coin.mohui_coin}")
    BAIT_MAP = {
        "普通饵料": "basic",
        "初级饵料": "intermediate",
        "中级饵料": "advanced",
        "高级饵料": "maximal"
    }
    bait_type = BAIT_MAP[bait_data['name']]
    await remove_mohui_coin(session=session, user_id=str(event.user_id), amount=total_price)
    await add_bait(session=session, user_id=str(event.user_id), bait_type=bait_type, amount=count)
    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"成功购买了{count}个{bait_data['name']}了捏~")


# 饵料反向查找
REVERSE_BAIT_MAP = {
    "basic": "普通饵料",
    "intermediate": "初级饵料",
    "advanced": "中级饵料",
    "maximal": "高级饵料"
}


@fishing_downswing.handle()
@handle_errors
async def _fishing_downswing(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
        args: Message = CommandArg()
) -> None:
    user_id = str(event.user_id)
    bait_arg = args.extract_plain_text().strip()

    # 1. 验证前置条件并确定饵料类型
    fishing_error, bait_type = await process_fishing(session=session, user_id=user_id, bait_name_arg=bait_arg)
    if fishing_error:
        await matcher.finish(MessageSegment.reply(event.message_id) + fishing_error)

    # 2. 扣除饵料
    await consume_bait(session=session, user_id=user_id, bait_type=bait_type)

    # 3. 计算当前的配置属性与咬钩延迟
    user_rod = await get_rod(session=session, user_id=user_id)
    rod_data = next((item for item in FishingRod.rod_attribute if item['name'] == user_rod),
                    FishingRod.rod_attribute[0])

    # 鱼竿决定起竿的等待窗口范围
    window_bonus = random.randint(rod_data['bonus_min'], rod_data['bonus_max'])

    # 获取所选饵料的加成值
    bait_data = next((item for item in FishingBait.bait_attribute if item['name'] == REVERSE_BAIT_MAP[bait_type]),
                     {"bonus": 0})
    bait_bonus = bait_data['bonus']

    # 随机 30~60 秒后鱼咬钩
    bite_delay = random.randint(30, 60)
    lure_end_time = time.time() + bite_delay

    # 4. 写入数据库抛竿状态
    await try_start_fishing(
        session=session,
        user_id=user_id,
        lure_end_time=lure_end_time,
        base_wait=bite_delay,
        window_bonus=window_bonus,
        bait_bonus=bait_bonus
    )

    run_date_aware = datetime.now().astimezone() + timedelta(seconds=bite_delay)
    logger.info(f"玩家 {user_id} 抛竿成功，预计在 {run_date_aware.strftime('%H:%M:%S')} 咬钩")

    scheduler.add_job(
        send_bite_reminder,
        "date",
        run_date=run_date_aware,  # 使用原生的绝对本地时间
        args=[user_id, event.group_id, window_bonus, event.self_id],
        id=f"fishing_{user_id}",
        replace_existing=True
    )

    await matcher.finish(MessageSegment.reply(
        event.message_id) + f"🎣 抛竿成功！使用了【{REVERSE_BAIT_MAP[bait_type]}】。静静等待鱼儿上钩吧 awa~")


async def send_bite_reminder(user_id: str, group_id: int, window_bonus: int, self_id):
    """APScheduler 触发的后台咬钩提醒回调"""
    from nonebot import get_bots, logger

    # 1. 获取当前所有在线的 Bot 实例
    bots = get_bots()
    if not bots:
        logger.error("没有在线的Bot实例，无法发送咬钩提醒")
        return

    # 2. 尝试精准匹配 self_id（将传入的 self_id 强制转为字符串以匹配字典键）
    bot = bots.get(str(self_id))

    # 3. 如果精准匹配失败（比如类型依然对不上，或多进程导致找不到），退而求其次取第一个可用的 Bot
    if not bot:
        bot = list(bots.values())[0]
        logger.warning(f"未找到 self_id={self_id} 的 Bot，已自动使用备选 Bot: {bot.self_id}")

    async with get_session() as session:
        state = await get_state(session, user_id)
        if not state or not state.is_fishing or state.reminder_sent:
            return

        now = time.time()
        # 此时鱼咬饵，设定起竿窗口（从当前时间起到加成时间结束）
        await set_pull_window(session, user_id, earliest=now, latest=now + window_bonus)

        # 遵循指令式原则，群内 At 提醒
        msg = MessageSegment.at(user_id) + f" 🎣 浮漂猛地一沉！有鱼咬钩了！请在 {window_bonus} 秒内快速发送“收竿”或“提竿”！"
        try:
            await bot.send_group_msg(group_id=group_id, message=msg)
        except Exception as e:
            logger.error(f"发送咬钩提醒失败: {e}")


@fishing_pull.handle()
@handle_errors
async def _fishing_pull(
        matcher: Matcher,
        event: GroupMessageEvent,
        session: async_scoped_session,
) -> None:
    user_id = str(event.user_id)

    # 1. 只要发送了起竿指令，立刻先行扣除 1 点鱼钩耐久
    hook_still_functional = await reduce_hook_durability(session=session, user_id=user_id)
    state = await get_state(session, user_id)
    if not state or not state.is_fishing:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你还没抛竿呢捏！快去发送“钓鱼”抛竿吧 awa")
    fishing_data = await get_fishing_data(session, user_id)

    # 2. 提竿过早：鱼还没咬钩（定时器未执行）
    if not state.reminder_sent:
        try:
            scheduler.remove_job(f"fishing_{user_id}")
        except Exception:
            pass
        await end_fishing(session, user_id)
        await matcher.finish(
            MessageSegment.reply(event.message_id) + "鱼还没咬钩呢！你收竿太急，把鱼儿吓跑了，白白浪费了饵料 qwq！")

    # 3. 提竿过晚：超时未提
    now = time.time()
    if now > state.latest_pull:
        await end_fishing(session, user_id)
        await matcher.finish(MessageSegment.reply(event.message_id) + "太晚了捏！鱼儿已经吃完饵脱钩溜走啦 qwq！")

    # 4. 成功起竿：在时间窗口范围内
    # 计算稀有概率加权总值（鱼钩加成 + 饵料加成）
    user_hook = fishing_data.fish_hook
    hook_info = next((item for item in FishingHook.hook_attribute if item['name'] == user_hook), {"bonus": 0})
    total_bonus = hook_info['bonus'] + state.bait_bonus

    # 稀有权重调整计算
    trash_w = max(0.0, float(Fish.trash["bonus"] - total_bonus))
    basic_w = float(Fish.basic_fish["bonus"])  # 普通鱼不计入权重加成
    inter_w = float(Fish.intermediate_fish["bonus"]) * (1.0 + total_bonus / 100.0)  # 稀有鱼加成
    advan_w = float(Fish.advanced_fish["bonus"]) * (1.0 + total_bonus / 100.0)  # 传说鱼加成

    categories = ["trash", "basic_fish", "intermediate_fish", "advanced_fish"]
    weights = [trash_w, basic_w, inter_w, advan_w]

    # 按权重随机抽取
    chosen_cat = random.choices(categories, weights=weights, k=1)[0]

    # 获取对应收益与品阶译名
    cat_details = {
        "trash": ("垃圾", Fish.trash["price"]),
        "basic_fish": ("普通鱼", Fish.basic_fish["price"]),
        "intermediate_fish": ("稀有鱼", Fish.intermediate_fish["price"]),
        "advanced_fish": ("传说鱼", Fish.advanced_fish["price"])
    }
    fish_chinese_name, reward_coin = cat_details[chosen_cat]

    # 结算奖励并重置玩家钓鱼状态
    user_coin = await get_mohui_data(session=session, user_id=user_id)
    user_coin.mohui_coin += reward_coin
    await end_fishing(session, user_id)

    # 鱼钩损坏提醒文案
    durability_tip = "" if hook_still_functional else "\n⚠️ 提示：您的鱼钩耐久已耗尽，已不幸损坏并从装备栏中卸下！"

    if chosen_cat == "trash":
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"🗑️ 感觉沉甸甸的...结果拉上来一看是个废弃垃圾！什么奖励都没有 qwq{durability_tip}")
    else:
        await matcher.finish(MessageSegment.reply(
            event.message_id) + f"🎉 收竿成功！你成功钓到了一只【{fish_chinese_name}】！获得了 {reward_coin} 墨辉币捏！{durability_tip}")