import random as rd
import time
from datetime import datetime

from nonebot import on_command, require
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_orm import async_scoped_session

from ..database.models import (
    add_inventory,
    get_fishing_session,
    get_inventory_qty,
    remove_inventory,
)
from ..entertainment.currency.exceptions import CurrencyBalanceNotEnough
from ..entertainment.currency.models import add_mohui_coin, remove_mohui_coin

scheduler = require("nonebot_plugin_apscheduler").scheduler

# ================= 配置 =================
# 鱼竿：6 阶，窗口增益上限 +40s；商店变体（价格系数, 耐久系数）
ROD_VARIANTS = {
    "标准": (1.0, 1.0),
    "廉价": (0.45, 0.3),
    "精良": (2.2, 2.5),
}
RODS = [
    {"id": "bamboo",   "name": "竹竿",    "bonus": 0,  "price": 100,  "dur": 50},
    {"id": "wood",     "name": "木竿",    "bonus": 5,  "price": 300,  "dur": 80},
    {"id": "fiber",    "name": "玻璃钢竿", "bonus": 12, "price": 1000, "dur": 120},
    {"id": "carbon",   "name": "碳素竿",  "bonus": 22, "price": 3000, "dur": 160},
    {"id": "titanium", "name": "钛合金竿", "bonus": 32, "price": 8000, "dur": 220},
    {"id": "legend",   "name": "传说·神竿", "bonus": 40, "price": 20000, "dur": 300},
]
# 鱼钩：4 阶，mult 为各鱼种档位权重倍率（仅影响鱼，不影响随机物品概率）
HOOKS = [
    {"id": "iron",   "name": "铁钩",   "price": 100,  "mult": [1, 1, 1, 1, 1, 1, 1, 1]},
    {"id": "silver", "name": "银钩",   "price": 500,  "mult": [1, 1, 1, 3, 3, 3, 4, 5]},
    {"id": "gold",   "name": "金钩",   "price": 2000, "mult": [1, 1, 1, 8, 8, 10, 14, 18]},
    {"id": "legend", "name": "传说钩", "price": 8000, "mult": [1, 1, 1, 20, 25, 35, 55, 80]},
]
# 鱼种：8 档，1-3 档无窗口减益，4-8 档有减益
FISH = [
    {"id": "t1", "name": "小杂鱼",    "price": 20,  "debuff": 0},
    {"id": "t2", "name": "鲫鱼",      "price": 50,  "debuff": 0},
    {"id": "t3", "name": "鲤鱼",      "price": 100, "debuff": 0},
    {"id": "t4", "name": "鲈鱼",      "price": 180, "debuff": 2},
    {"id": "t5", "name": "鲑鱼",      "price": 300, "debuff": 4},
    {"id": "t6", "name": "金枪鱼",    "price": 550, "debuff": 6},
    {"id": "t7", "name": "蓝鳍金枪",  "price": 1000, "debuff": 8},
    {"id": "t8", "name": "传说·龙鲤", "price": 2500, "debuff": 12},
]
_BASE_WEIGHTS = [45.0, 25.0, 15.0, 8.0, 4.0, 2.5, 0.4, 0.1]
BAIT_PRICE = 10

_ROD_BY_NAME = {r["name"]: r for r in RODS}
_ROD_BY_ID = {r["id"]: r for r in RODS}
_HOOK_BY_NAME = {h["name"]: h for h in HOOKS}
_HOOK_BY_ID = {h["id"]: h for h in HOOKS}
_FISH_BY_ID = {f["id"]: f for f in FISH}

# 时间参数（秒）
BITE_RANGE = (10, 30)      # 抛竿 -> 上钩
WAIT_RANGE = (10, 20)      # 上钩 -> 窗口开启（溜鱼）
WINDOW_BASE_RANGE = (3, 10)  # 基础窗口长度
MIN_WINDOW = 3

# 随机物品事件：总概率固定 8%，不受鱼钩影响
ITEM_CHEST_P = 0.025    # 宝箱 +100~500
ITEM_JUNK_P = 0.03      # 垃圾 无收益
# 剩余 0.025 = 倒霉事件 -50~-300


def resolve_rod(text: str):
    text = text.strip().replace(" ", "")
    return _ROD_BY_ID.get(text) or _ROD_BY_NAME.get(text)


def resolve_hook(text: str):
    text = text.strip().replace(" ", "")
    return _HOOK_BY_ID.get(text) or _HOOK_BY_NAME.get(text)


def roll_outcome(hook_id: str | None) -> str:
    """返回 outcome 字符串：fish:<id> / item:chest / item:junk / item:badluck。"""
    r = rd.random()
    if r < ITEM_CHEST_P:
        return "item:chest"
    if r < ITEM_CHEST_P + ITEM_JUNK_P:
        return "item:junk"
    if r < 0.08:
        return "item:badluck"
    hook = _HOOK_BY_ID.get(hook_id) if hook_id else None
    mult = hook["mult"] if hook else [1] * 8
    weights = [b * m for b, m in zip(_BASE_WEIGHTS, mult)]
    idx = rd.choices(range(8), weights=weights)[0]
    return f"fish:{FISH[idx]['id']}"


async def spend_coins(session, user_id: str, amount: int) -> bool:
    try:
        await remove_mohui_coin(session, user_id, amount)
        return True
    except CurrencyBalanceNotEnough:
        return False


# ================= 定时推送：鱼上钩 =================
async def _send_bite(user_id: str, group_id: str, wait: int):
    """抛竿后 bite_at 时刻触发：向玩家所在群推送"鱼上钩"（纯消息，无 DB 依赖）。"""
    try:
        from nonebot import get_bot
        bot = get_bot()
        await bot.send_group_msg(
            group_id=int(group_id),
            message=f"🐟 鱼上钩了！正在溜鱼，预计约 {max(1, wait)} 秒后进入收竿窗口，请在窗口期内发送「收竿」！",
        )
    except Exception:
        pass


def _cancel_bite_job(user_id: str):
    try:
        scheduler.remove_job(f"fishing_bite_{user_id}")
    except Exception:
        pass


# ================= 命令 =================
_cast = on_command("钓鱼", block=True)
_pull = on_command("收竿", aliases={"提竿"}, block=True)
_buy_rod = on_command("购买鱼竿", block=True)
_buy_hook = on_command("购买鱼钩", block=True)
_buy_bait = on_command("购买饵料", block=True)
_rod_info = on_command("鱼竿属性", block=True)
_hook_info = on_command("鱼钩属性", block=True)
_bait_info = on_command("饵料属性", block=True)


@_cast.handle()
async def _handle_cast(matcher: Matcher, event: GroupMessageEvent,
                       session: async_scoped_session):
    user_id = str(event.user_id)
    s = await get_fishing_session(session, user_id)
    now = int(time.time())
    # 清理过期会话
    if s.state == "fishing" and now > s.window_end + 60:
        s.state = None
        await session.flush()
    if s.state == "fishing":
        await matcher.finish(MessageSegment.reply(event.message_id) + "你已经在钓鱼啦，先收竿再抛竿哦")
    # 装备检查
    if not s.hook_id:
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "没有鱼钩是无法钓鱼的哦！发送「购买鱼钩 铁钩」先买一个鱼钩吧")
    if not s.rod_id:
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "你还没有鱼竿！发送「购买鱼竿 竹竿」先买一根鱼竿吧")
    if s.rod_durability <= 0:
        await matcher.finish(MessageSegment.reply(event.message_id) + "你的鱼竿已经损毁了，请重新「购买鱼竿」")
    if await get_inventory_qty(session, user_id, "bait") < 1:
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "你没有饵料了！发送「购买饵料 <数量>」补充吧")
    # 消耗
    await remove_inventory(session, user_id, "bait", 1)
    s.rod_durability -= 1
    # rod_id 形如 carbon_标准，需去掉变体后缀再查配置
    rod = _ROD_BY_ID.get(s.rod_id.split("_", 1)[0]) if s.rod_id else None
    rod_bonus = rod["bonus"] if rod else 0
    # 掷结果
    outcome = roll_outcome(s.hook_id)
    if outcome.startswith("fish:"):
        fish = _FISH_BY_ID[outcome.split(":", 1)[1]]
        debuff = fish["debuff"]
    else:
        debuff = 0
    # 时间线
    bite_at = now + rd.randint(*BITE_RANGE)
    wait = rd.randint(*WAIT_RANGE)
    window_start = bite_at + wait
    window_len = max(MIN_WINDOW, rd.randint(*WINDOW_BASE_RANGE) + rod_bonus - debuff)
    window_end = window_start + window_len
    s.group_id = str(event.group_id)
    s.state = "fishing"
    s.cast_at = now
    s.bite_at = bite_at
    s.window_start = window_start
    s.window_end = window_end
    s.outcome = outcome
    await session.commit()
    # 定时推送上钩（wait = 溜鱼秒数）
    scheduler.add_job(
        _send_bite, "date", run_date=datetime.fromtimestamp(bite_at),
        args=[user_id, s.group_id, wait], id=f"fishing_bite_{user_id}", replace_existing=True,
    )
    broken = ""
    if s.rod_durability <= 0:
        broken = "\n（你的鱼竿耐久耗尽，已经损毁了！）"
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"🎣 你抛出了鱼钩，静静等待鱼儿上钩…（预计 10~30 秒后会有动静）{broken}")


@_pull.handle()
async def _handle_pull(matcher: Matcher, event: GroupMessageEvent,
                       session: async_scoped_session):
    user_id = str(event.user_id)
    s = await get_fishing_session(session, user_id)
    if s.state != "fishing":
        await matcher.finish(MessageSegment.reply(event.message_id) + "你还没有在钓鱼哦，发送「钓鱼」抛竿吧")
    now = int(time.time())
    if now < s.window_start:
        # 过早
        s.state = None
        _cancel_bite_job(user_id)
        await session.commit()
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "太心急了！鱼被你吓跑了…（下次等窗口开启后再收竿哦）")
    if now > s.window_end:
        # 过晚
        s.state = None
        _cancel_bite_job(user_id)
        await session.commit()
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "收竿太晚了！鱼已经挣脱溜走了…")
    # 窗口期内：上鱼！
    s.state = None
    _cancel_bite_job(user_id)
    outcome = s.outcome
    if outcome.startswith("fish:"):
        fish = _FISH_BY_ID[outcome.split(":", 1)[1]]
        await add_mohui_coin(session, user_id, fish["price"])
        await session.commit()
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             f"🎣 上鱼了！你钓到了【{fish['name']}】！价值 {fish['price']} 墨辉币，已自动出售！")
    elif outcome == "item:chest":
        coins = rd.randint(100, 500)
        await add_mohui_coin(session, user_id, coins)
        await session.commit()
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             f"🎁 你钓上来一只宝箱！打开获得 {coins} 墨辉币！")
    elif outcome == "item:junk":
        await session.commit()
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "👢 你钓上来一只旧靴子…看了看又扔回水里了（一无所获）")
    else:  # item:badluck
        amount = rd.randint(50, 300)
        try:
            await remove_mohui_coin(session, user_id, amount)
            await session.commit()
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 f"😱 你钓上来一只水鬼！被抢走了 {amount} 墨辉币！")
        except CurrencyBalanceNotEnough:
            await session.commit()
            await matcher.finish(MessageSegment.reply(event.message_id) +
                                 "😅 你钓上来一只水鬼，但它看你太穷了，没抢到钱就游走了…")


@_buy_rod.handle()
async def _handle_buy_rod(matcher: Matcher, event: GroupMessageEvent,
                          session: async_scoped_session, args: Message = CommandArg()):
    parts = args.extract_plain_text().split()
    if not parts:
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "用法：购买鱼竿 <品阶> [标准|廉价|精良]\n品阶：竹竿/木竿/玻璃钢竿/碳素竿/钛合金竿/传说·神竿")
    rod = resolve_rod(parts[0])
    if rod is None:
        await matcher.finish(MessageSegment.reply(event.message_id) + "没有这种鱼竿，发送「鱼竿属性」查看商店")
    variant = "标准"
    if len(parts) > 1:
        v = parts[1].strip()
        if v in ROD_VARIANTS:
            variant = v
    p_mult, d_mult = ROD_VARIANTS[variant]
    price = max(1, round(rod["price"] * p_mult))
    dur = max(1, round(rod["dur"] * d_mult))
    user_id = str(event.user_id)
    if not await spend_coins(session, user_id, price):
        await matcher.finish(MessageSegment.reply(event.message_id) + f"需要 {price} 墨辉币，余额不足！")
    s = await get_fishing_session(session, user_id)
    old = s.rod_id
    s.rod_id = f"{rod['id']}_{variant}"
    s.rod_durability = dur
    await session.commit()
    msg = (f"已购买并装备【{rod['name']}·{variant}】（{price} 墨辉币，耐久 {dur}）。"
           f"窗口增益 +{rod['bonus']}s")
    if old:
        msg += f"\n（旧鱼竿已被替换回收）"
    await matcher.finish(MessageSegment.reply(event.message_id) + msg)


@_buy_hook.handle()
async def _handle_buy_hook(matcher: Matcher, event: GroupMessageEvent,
                           session: async_scoped_session, args: Message = CommandArg()):
    parts = args.extract_plain_text().split()
    if not parts:
        await matcher.finish(MessageSegment.reply(event.message_id) +
                             "用法：购买鱼钩 <品阶>\n品阶：铁钩/银钩/金钩/传说钩")
    hook = resolve_hook(parts[0])
    if hook is None:
        await matcher.finish(MessageSegment.reply(event.message_id) + "没有这种鱼钩，发送「鱼钩属性」查看商店")
    user_id = str(event.user_id)
    if not await spend_coins(session, user_id, hook["price"]):
        await matcher.finish(MessageSegment.reply(event.message_id) + f"需要 {hook['price']} 墨辉币，余额不足！")
    s = await get_fishing_session(session, user_id)
    s.hook_id = hook["id"]
    await session.commit()
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已购买并装备【{hook['name']}】（{hook['price']} 墨辉币）")


@_buy_bait.handle()
async def _handle_buy_bait(matcher: Matcher, event: GroupMessageEvent,
                           session: async_scoped_session, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    qty = 1
    if text.isdigit():
        qty = max(1, int(text))
    cost = qty * BAIT_PRICE
    user_id = str(event.user_id)
    if not await spend_coins(session, user_id, cost):
        await matcher.finish(MessageSegment.reply(event.message_id) + f"需要 {cost} 墨辉币，余额不足！")
    await add_inventory(session, user_id, "bait", qty)
    await session.commit()
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"已购买饵料 x{qty}（花费 {cost} 墨辉币），每次钓鱼消耗 1 个")


@_rod_info.handle()
async def _handle_rod_info(matcher: Matcher, event: GroupMessageEvent,
                           session: async_scoped_session):
    user_id = str(event.user_id)
    s = await get_fishing_session(session, user_id)
    lines = ["【鱼竿属性】"]
    if s.rod_id:
        base, variant = (s.rod_id.split("_", 1) + ["标准"])[:2]
        rod = _ROD_BY_ID.get(base)
        if rod:
            lines.append(f"当前：{rod['name']}·{variant}（耐久 {s.rod_durability}/{rod['dur']}，窗口增益 +{rod['bonus']}s）")
        else:
            lines.append("当前：未知鱼竿")
    else:
        lines.append("当前：无鱼竿")
    lines.append("商店（品阶 | 标准价/耐久 | 廉价 | 精良）：")
    for rod in RODS:
        cheap_p, cheap_d = ROD_VARIANTS["廉价"]
        delux_p, delux_d = ROD_VARIANTS["精良"]
        lines.append(f"· {rod['name']}：{rod['price']}/{rod['dur']} | "
                     f"{round(rod['price']*cheap_p)}/{round(rod['dur']*cheap_d)} | "
                     f"{round(rod['price']*delux_p)}/{round(rod['dur']*delux_d)}"
                     f"（增益+{rod['bonus']}s）")
    lines.append("发送「购买鱼竿 <品阶> [标准|廉价|精良]」购买")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))


@_hook_info.handle()
async def _handle_hook_info(matcher: Matcher, event: GroupMessageEvent,
                            session: async_scoped_session):
    user_id = str(event.user_id)
    s = await get_fishing_session(session, user_id)
    lines = ["【鱼钩属性】"]
    if s.hook_id and _HOOK_BY_ID.get(s.hook_id):
        lines.append(f"当前：{_HOOK_BY_ID[s.hook_id]['name']}")
    else:
        lines.append("当前：无鱼钩（没有鱼钩无法钓鱼！）")
    lines.append("商店（品阶 | 价格 | 稀有鱼概率）：")
    for hook in HOOKS:
        lines.append(f"· {hook['name']}：{hook['price']} 墨辉币")
    lines.append("发送「购买鱼钩 <品阶>」购买")
    await matcher.finish(MessageSegment.reply(event.message_id) + MessageSegment.text("\n".join(lines)))


@_bait_info.handle()
async def _handle_bait_info(matcher: Matcher, event: GroupMessageEvent,
                            session: async_scoped_session):
    user_id = str(event.user_id)
    qty = await get_inventory_qty(session, user_id, "bait")
    await matcher.finish(MessageSegment.reply(event.message_id) +
                         f"【饵料】单价 {BAIT_PRICE} 墨辉币/个，你当前有 {qty} 个。发送「购买饵料 <数量>」补充")
