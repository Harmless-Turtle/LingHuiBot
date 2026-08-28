import random as rd
import time
from datetime import date

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from ..database.models import (
    FarmPlot,
    add_farm_plot,
    add_inventory,
    clear_farm_plot,
    get_farm_plot,
    get_farm_plots,
    get_inventory_qty,
    plant_crop,
    remove_inventory,
)
from ..entertainment.currency.exceptions import CurrencyBalanceNotEnough
from ..entertainment.currency.models import add_mohui_coin, remove_mohui_coin

# ================= 作物配置 =================
# id: 名称 / 种子价 / 生长秒数 / 单块产量范围 / 基准售价 / 收割返还种子概率
CROPS: dict[str, dict] = {
    "wheat":      {"name": "小麦",   "seed_price": 100,  "grow": 8 * 3600,   "ymin": 2, "ymax": 4, "base": 50,  "seed_back": 0.7},
    "carrot":     {"name": "胡萝卜", "seed_price": 150,  "grow": 12 * 3600,  "ymin": 1, "ymax": 3, "base": 85,  "seed_back": 0.5},
    "tomato":     {"name": "番茄",   "seed_price": 250,  "grow": 20 * 3600,  "ymin": 3, "ymax": 5, "base": 65,  "seed_back": 0.5},
    "corn":       {"name": "玉米",   "seed_price": 300,  "grow": 24 * 3600,  "ymin": 4, "ymax": 6, "base": 70,  "seed_back": 0.7},
    "strawberry": {"name": "草莓",   "seed_price": 400,  "grow": 36 * 3600,  "ymin": 2, "ymax": 4, "base": 150, "seed_back": 0.3},
    "ginseng":    {"name": "黄金参", "seed_price": 1000, "grow": 72 * 3600,  "ymin": 1, "ymax": 2, "base": 750, "seed_back": 0.05},
}

# 中文名 -> 作物 id
_NAME_TO_ID = {info["name"]: cid for cid, info in CROPS.items()}


def resolve_crop(text: str) -> str | None:
    """把用户输入（中文名或 id）解析为作物 id。"""
    text = text.strip()
    if text in CROPS:
        return text
    return _NAME_TO_ID.get(text)


def today_price(crop_id: str) -> int:
    """按日期确定当日售价（全服同价），下限为种子价。"""
    info = CROPS[crop_id]
    rng = rd.Random(f"{date.today().isoformat()}:farm:{crop_id}")
    return max(info["seed_price"], int(info["base"] * rng.uniform(0.8, 1.2)))


def land_price(current_count: int) -> int:
    """开荒第 current_count+1 块地的价格：2-10 块固定 1000，之后指数增长。"""
    n = current_count + 1
    if n <= 10:
        return 1000
    return int(1000 * (1.5 ** (n - 10)))


async def spend_coins(session, user_id: str, amount: int) -> bool:
    """从墨辉币扣款，余额不足返回 False。"""
    try:
        await remove_mohui_coin(session, user_id, amount)
        return True
    except CurrencyBalanceNotEnough:
        return False


async def ensure_default_plot(session, user_id: str) -> list:
    """每位玩家默认拥有第 1 块地（免费），首次访问自动发放。"""
    plots = await get_farm_plots(session, user_id)
    if not plots:
        session.add(FarmPlot(user_id=user_id, plot_index=1, crop_id=None, planted_at=None))
        await session.flush()
        plots = await get_farm_plots(session, user_id)
    return plots


# ================= 命令 =================
_kaifang = on_command("开荒", block=True)
_seed_shop = on_command("种子商店", aliases={"种子市场"}, block=True)
_buy_seed = on_command("购买种子", block=True)
_plant = on_command("种植", block=True)
_my_farm = on_command("我的农场", aliases={"农场"}, block=True)
_harvest = on_command("收割", block=True)
_sell = on_command("出售", block=True)
_market = on_command("市场", aliases={"行情"}, block=True)


@_kaifang.handle()
async def _handle_kaifang(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session):
    user_id = str(event.user_id)
    plots = await ensure_default_plot(session, user_id)
    price = land_price(len(plots))
    if not await spend_coins(session, user_id, price):
        await matcher.finish(MessageSegment.reply(event.message_id) + f"开荒需要 {price} 墨辉币，你的余额不足！")
    plot = await add_farm_plot(session, user_id)
    await session.commit()
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"开荒成功！你获得了第 {plot.plot_index} 块地（花费 {price} 墨辉币）。"
                         f"\n当前共 {plot.plot_index} 块地，下一块开荒需要 {land_price(plot.plot_index)} 墨辉币。")


@_seed_shop.handle()
async def _handle_seed_shop(matcher: Matcher, event: GroupMessageEvent,
                            session: async_scoped_session):
    lines = ["【种子商店】", "作物 | 种子价 | 生长周期 | 单块产量 | 售价区间"]
    for cid, info in CROPS.items():
        grow_h = round(info["grow"] / 3600, 1)
        lines.append(f"{info['name']} | {info['seed_price']} | {grow_h}小时 | {info['ymin']}-{info['ymax']} | {info['base'] * 0.8:.0f}-{info['base'] * 1.2:.0f}")
    lines.append("发送「购买种子 <作物> <数量>」购买种子")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))


@_buy_seed.handle()
async def _handle_buy_seed(matcher: Matcher, event: GroupMessageEvent,
                           session: async_scoped_session, args: Message = CommandArg()):
    parts = args.extract_plain_text().split()
    if not parts:
        await matcher.finish(MessageSegment.reply(event.message_id) + "用法：购买种子 <作物> [数量]")
    crop_id = resolve_crop(parts[0])
    if crop_id is None:
        await matcher.finish(MessageSegment.reply(event.message_id) + "没有这种作物哦，发送「种子商店」查看列表")
    qty = 1
    if len(parts) > 1 and parts[1].isdigit():
        qty = max(1, int(parts[1]))
    info = CROPS[crop_id]
    cost = info["seed_price"] * qty
    if not await spend_coins(session, str(event.user_id), cost):
        await matcher.finish(MessageSegment.reply(event.message_id) + f"需要 {cost} 墨辉币，余额不足！")
    await add_inventory(session, str(event.user_id), f"seed_{crop_id}", qty)
    await session.commit()
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已购买 {info['name']}种子 x{qty}（花费 {cost} 墨辉币）。发送「种植 {info['name']}」播种")


@_plant.handle()
async def _handle_plant(matcher: Matcher, event: GroupMessageEvent,
                        session: async_scoped_session, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    parts = text.split()
    if not parts:
        await matcher.finish(MessageSegment.reply(event.message_id) + "用法：种植 <作物> [第X块地]")
    crop_id = resolve_crop(parts[0])
    if crop_id is None:
        await matcher.finish(MessageSegment.reply(event.message_id) + "没有这种作物哦，发送「种子商店」查看列表")
    user_id = str(event.user_id)
    seed_item = f"seed_{crop_id}"
    if await get_inventory_qty(session, user_id, seed_item) < 1:
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             f"你没有{CROPS[crop_id]['name']}种子，先「购买种子 {CROPS[crop_id]['name']}」吧")
    plots = await ensure_default_plot(session, user_id)
    await session.commit()  # 确保新玩家默认地块持久化（后续可能提前 finish）
    if not plots:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你还没有地块，先「开荒」吧")
    # 指定地块
    target_index = None
    for part in parts[1:]:
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            target_index = int(digits)
            break
    if target_index is not None:
        plot = await get_farm_plot(session, user_id, target_index)
        if plot is None:
            await matcher.finish(MessageSegment.reply(event.message_id) + f"没有第 {target_index} 块地哦")
        if plot.crop_id is not None:
            await matcher.finish(MessageSegment.reply(event.message_id) + f"第 {target_index} 块地已有作物，无法种植")
    else:
        # 自动选第一块空闲地
        plot = next((p for p in plots if p.crop_id is None), None)
        if plot is None:
            await matcher.finish(MessageSegment.reply(event.message_id) + "所有地块都种满啦，先「收割」或「开荒」吧")
    if not await remove_inventory(session, user_id, seed_item, 1):
        await matcher.finish(MessageSegment.reply(event.message_id) + "种子不足")
    await plant_crop(session, user_id, plot.plot_index, crop_id, int(time.time()))
    await session.commit()
    info = CROPS[crop_id]
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已在第 {plot.plot_index} 块地种下{info['name']}！约 {round(info['grow'] / 3600, 1)} 小时后成熟，"
                         f"发送「收割」即可收获")


@_my_farm.handle()
async def _handle_my_farm(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session):
    user_id = str(event.user_id)
    plots = await ensure_default_plot(session, user_id)
    await session.commit()  # 确保新玩家默认地块持久化
    now = int(time.time())
    lines = [f"【{user_id} 的农场】（共 {len(plots)} 块地）"]
    idle = 0
    for p in plots:
        if p.crop_id is None:
            idle += 1
            continue
        info = CROPS[p.crop_id]
        remain = p.planted_at + info["grow"] - now
        if remain <= 0:
            lines.append(f"· 第{p.plot_index}块地：{info['name']} ✅已成熟，可收割")
        else:
            h = remain // 3600
            m = (remain % 3600) // 60
            lines.append(f"· 第{p.plot_index}块地：{info['name']} 还有 {h}小时{m}分 成熟")
    if idle:
        lines.append(f"· 空闲地块 x{idle}")
    lines.append("今日售价：")
    for cid in CROPS:
        lines.append(f"  {CROPS[cid]['name']} {today_price(cid)} 墨辉币")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))


@_harvest.handle()
async def _handle_harvest(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session, args: Message = CommandArg()):
    user_id = str(event.user_id)
    text = args.extract_plain_text().strip()
    now = int(time.time())
    plots = await get_farm_plots(session, user_id)
    if not plots:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你还没有地块哦")
    # 目标地块集合
    target_index = None
    for ch in text:
        if ch.isdigit():
            target_index = int("".join(c for c in text if c.isdigit()))
            break
    harvested = []
    for p in plots:
        if p.crop_id is None:
            continue
        if target_index is not None and p.plot_index != target_index:
            continue
        info = CROPS[p.crop_id]
        if p.planted_at + info["grow"] > now:
            continue
        # 产量：单块随机 min..max，多块求和（极端概率小）
        yield_total = rd.randint(info["ymin"], info["ymax"])
        harvested.append((p.plot_index, p.crop_id, yield_total, info))
        await add_inventory(session, user_id, p.crop_id, yield_total)
        # 返还种子（概率）
        if rd.random() < info["seed_back"]:
            await add_inventory(session, user_id, f"seed_{p.crop_id}", 1)
        await clear_farm_plot(session, user_id, p.plot_index)
    if not harvested:
        msg = "没有可收割的成熟作物" if target_index is None else f"第 {target_index} 块地没有可收割的成熟作物"
        await matcher.finish(MessageSegment.reply(event.message_id) + msg)
    await session.commit()
    lines = ["收割完成："]
    total_produce = 0
    for idx, cid, y, info in harvested:
        lines.append(f"· 第{idx}块地：{info['name']} x{y}")
        total_produce += y
    lines.append(f"产物已放入背包，发送「出售 {CROPS[harvested[0][1]]['name']}」按今日价格卖出")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))


@_sell.handle()
async def _handle_sell(matcher: Matcher, event: GroupMessageEvent,
                       session: async_scoped_session, args: Message = CommandArg()):
    parts = args.extract_plain_text().split()
    if not parts:
        await matcher.finish(MessageSegment.reply(event.message_id) + "用法：出售 <作物> [数量|全部]")
    crop_id = resolve_crop(parts[0])
    if crop_id is None:
        await matcher.finish(MessageSegment.reply(event.message_id) + "没有这种作物哦")
    user_id = str(event.user_id)
    have = await get_inventory_qty(session, user_id, crop_id)
    if have <= 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"你背包里没有{CROPS[crop_id]['name']}产物")
    qty = have
    if len(parts) > 1 and parts[1].isdigit():
        qty = int(parts[1])
    if qty > have:
        await matcher.finish(MessageSegment.reply(event.message_id) + f"你只有 {have} 个{CROPS[crop_id]['name']}")
    price = today_price(crop_id)
    if not await remove_inventory(session, user_id, crop_id, qty):
        await matcher.finish(MessageSegment.reply(event.message_id) + "出售失败（数量不足）")
    income = price * qty
    await add_mohui_coin(session, user_id, income)
    await session.commit()
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已出售{CROPS[crop_id]['name']} x{qty}，今日单价 {price}，获得 {income} 墨辉币！")


@_market.handle()
async def _handle_market(matcher: Matcher, event: GroupMessageEvent,
                         session: async_scoped_session):
    lines = [f"【今日行情】{date.today().isoformat()}（全服同价）"]
    for cid, info in CROPS.items():
        lines.append(f"· {info['name']}：今日 {today_price(cid)} / 种子价 {info['seed_price']}")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))
