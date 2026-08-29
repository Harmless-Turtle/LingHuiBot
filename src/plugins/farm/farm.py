import random as rd
from datetime import date, datetime, timedelta, timezone

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from ..database.models import add_inventory, get_inventory_qty, remove_inventory
from .models import (
    FarmPlot,
    add_farm_plot,
    clear_farm_plot,
    get_farm_plot,
    get_farm_plots,
    plant_crop,
)
from ..entertainment.currency.exceptions import CurrencyBalanceNotEnough
from ..entertainment.currency.models import add_mohui_coin, remove_mohui_coin
from ..utils import batch_get, handle_errors
from .exceptions import FarmBalanceNotEnough, FarmError

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


async def spend_coins(session, user_id: str, amount: int) -> None:
    """从墨辉币扣款，余额不足抛 FarmBalanceNotEnough（由上层 handler 捕获）。"""
    try:
        await remove_mohui_coin(session, user_id, amount)
    except CurrencyBalanceNotEnough:
        raise FarmBalanceNotEnough() from None


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
@handle_errors
async def _handle_kaifang(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session, args: Message = CommandArg()):
    try:
        user_id = str(event.user_id)
        text = args.extract_plain_text().strip()
        # 只发「开荒」默认开荒 1 块；「开荒 N」批量开荒 N 块
        n = 1
        if text.isdigit() and int(text) > 0:
            n = int(text)
        # 防御：限制单次批量上限，避免误输入超大数字导致巨额计价/长循环
        MAX_BATCH = 20
        if n > MAX_BATCH:
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 f"单次最多开荒 {MAX_BATCH} 块，请分批开荒！")
        plots = await ensure_default_plot(session, user_id)
        count = len(plots)
        # 逐块计价（每块按当前地块数定价），计算批量总价
        prices = []
        for _ in range(n):
            p = land_price(count)
            prices.append(p)
            count += 1
        total_price = sum(prices)
        try:
            await spend_coins(session, user_id, total_price)
        except FarmBalanceNotEnough:
            raise FarmBalanceNotEnough(
                f"开荒 {n} 块地共需 {total_price} 墨辉币，你的余额不足！") from None
        # 实际添加地块（commit 前取值，避免 commit 后访问失效属性）
        new_indices = []
        for _ in range(n):
            plot = await add_farm_plot(session, user_id)
            new_indices.append(plot.plot_index)
        await session.commit()
        if n == 1:
            idx = new_indices[0]
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 f"开荒成功！你获得了第 {idx} 块地（花费 {prices[0]} 墨辉币）。"
                                 f"\n当前共 {idx} 块地，下一块开荒需要 {land_price(idx)} 墨辉币。")
        else:
            first, last = new_indices[0], new_indices[-1]
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 f"开荒成功！你获得了第 {first}~{last} 块地（共 {n} 块，花费 {total_price} 墨辉币）。"
                                 f"\n当前共 {last} 块地，下一块开荒需要 {land_price(last)} 墨辉币。")
    except FarmError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)


@_seed_shop.handle()
@handle_errors
async def _handle_seed_shop(matcher: Matcher, event: GroupMessageEvent, bot: Bot,
                            session: async_scoped_session):
    nodes = [await batch_get("【种子商店】", None, event.self_id, "种子商店")]
    for cid, info in CROPS.items():
        grow_h = round(info["grow"] / 3600, 1)
        nodes.append(await batch_get(
            f"{info['name']} | 种子价 {info['seed_price']} | {grow_h}小时 | "
            f"产量 {info['ymin']}-{info['ymax']} | 售价 {info['base'] * 0.8:.0f}-{info['base'] * 1.2:.0f}",
            None, event.self_id, "种子商店"))
    nodes.append(await batch_get("发送「购买种子 <作物> <数量>」购买种子", None, event.self_id, "种子商店"))
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=nodes, time_noend=True)
    await matcher.finish()


@_buy_seed.handle()
@handle_errors
async def _handle_buy_seed(matcher: Matcher, event: GroupMessageEvent,
                           session: async_scoped_session, args: Message = CommandArg()):
    try:
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
        try:
            await spend_coins(session, str(event.user_id), cost)
        except FarmBalanceNotEnough:
            raise FarmBalanceNotEnough(f"需要 {cost} 墨辉币，余额不足！") from None
        await add_inventory(session, str(event.user_id), f"seed_{crop_id}", qty)
        await session.commit()
    except FarmError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已购买 {info['name']}种子 x{qty}（花费 {cost} 墨辉币）。发送「种植 {info['name']}」播种")


@_plant.handle()
@handle_errors
async def _handle_plant(matcher: Matcher, event: GroupMessageEvent,
                        session: async_scoped_session, args: Message = CommandArg()):
    try:
        parts = args.extract_plain_text().split()
        if not parts:
            await matcher.finish(MessageSegment.reply(event.message_id) + "用法：种植 <作物>")
        crop_id = resolve_crop(parts[0])
        if crop_id is None:
            await matcher.finish(MessageSegment.reply(event.message_id) + "没有这种作物哦，发送「种子商店」查看列表")
        user_id = str(event.user_id)
        seed_item = f"seed_{crop_id}"
        info = CROPS[crop_id]
        plots = await ensure_default_plot(session, user_id)
        plot_count = len(plots)
        seed_have = await get_inventory_qty(session, user_id, seed_item)
        # 所有地块只允许种植同种作物：种子数须 ≥ 地块数
        if plot_count > seed_have:
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 f"种子不够！你共 {plot_count} 块地，需要 {plot_count} 颗{info['name']}种子，"
                                 f"当前只有 {seed_have} 颗。发送「购买种子 {info['name']}」补充")
        if any(p.crop_id is not None for p in plots):
            await matcher.finish(MessageSegment.reply(event.message_id) + "有未收割的作物，先「收割」再种植")
        if not await remove_inventory(session, user_id, seed_item, plot_count):
            await matcher.finish(MessageSegment.reply(event.message_id) + "种子不足")
        # 全部地块同时种下同一作物（标准 UTC）
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        for p in plots:
            await plant_crop(session, user_id, p.plot_index, crop_id, now_utc)
        grow_h = round(info["grow"] / 3600, 1)
        await session.commit()
    except FarmError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已在全部 {plot_count} 块地种下{info['name']}！约 {grow_h} 小时后成熟，"
                         f"发送「收割」即可收获")


@_my_farm.handle()
@handle_errors
async def _handle_my_farm(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session):
    try:
        user_id = str(event.user_id)
        plots = await ensure_default_plot(session, user_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        plot_count = len(plots)
        planted = [p for p in plots if p.crop_id is not None]
        if not planted:
            await session.commit()  # 持久化新玩家的默认地块
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 f"【你的农场】共 {plot_count} 块地\n目前全部空闲，发送「种植 <作物>」播种")
        # 统一作物：所有地块同种，取第一块地信息即可
        p0 = planted[0]
        info = CROPS[p0.crop_id]
        remain = p0.planted_at + timedelta(seconds=info["grow"]) - now
        if remain.total_seconds() <= 0:
            status = "✅ 已成熟，发送「收割」即可收获"
        else:
            secs = int(remain.total_seconds())
            h = secs // 3600
            m = (secs % 3600) // 60
            status = f"还有 {h} 小时 {m} 分成熟"
        # 属性访问完成后提交（持久化新玩家的默认地块）
        await session.commit()
    except FarmError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"【你的农场】共 {plot_count} 块地\n作物：{info['name']}\n状态：{status}\n发送「市场」查看今日价格")


@_harvest.handle()
@handle_errors
async def _handle_harvest(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session):
    try:
        user_id = str(event.user_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        plots = await get_farm_plots(session, user_id)
        if not plots:
            await matcher.finish(MessageSegment.reply(event.message_id) + "你还没有地块哦")
        harvested = []
        for p in plots:
            if p.crop_id is None:
                continue
            info = CROPS[p.crop_id]
            if p.planted_at + timedelta(seconds=info["grow"]) > now:
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
            # 有未成熟作物则提示剩余时间
            planted = [p for p in plots if p.crop_id is not None]
            if planted:
                info = CROPS[planted[0].crop_id]
                remain = planted[0].planted_at + timedelta(seconds=info["grow"]) - now
                secs = int(remain.total_seconds())
                h = secs // 3600
                m = (secs % 3600) // 60
                await matcher.finish(MessageSegment.reply(event.message_id) +
                                     f"作物还没成熟哦，{info['name']} 还有 {h} 小时 {m} 分成熟")
            await matcher.finish(MessageSegment.reply(event.message_id) + "没有可收割的作物")
        await session.commit()
    except FarmError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    lines = ["收割完成："]
    total = 0
    for idx, cid, y, info in harvested:
        lines.append(f"· 第{idx}块地：{info['name']} x{y}")
        total += y
    name = harvested[0][3]["name"]
    lines.append(f"共收获 {total} 个{name}，产物已放入背包。发送「出售 {name}」按今日价格卖出")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))


@_sell.handle()
@handle_errors
async def _handle_sell(matcher: Matcher, event: GroupMessageEvent,
                       session: async_scoped_session, args: Message = CommandArg()):
    try:
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
    except FarmError as e:
        await matcher.finish(MessageSegment.reply(event.message_id) + e.message)
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已出售{CROPS[crop_id]['name']} x{qty}，今日单价 {price}，获得 {income} 墨辉币！")


@_market.handle()
@handle_errors
async def _handle_market(matcher: Matcher, event: GroupMessageEvent, bot: Bot,
                         session: async_scoped_session):
    nodes = [await batch_get(f"【今日行情】{date.today().isoformat()}（全服同价）",
                             None, event.self_id, "今日行情")]
    for cid, info in CROPS.items():
        nodes.append(await batch_get(
            f"· {info['name']}：今日 {today_price(cid)} / 种子价 {info['seed_price']}",
            None, event.self_id, "今日行情"))
    await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=nodes, time_noend=True)
    await matcher.finish()
