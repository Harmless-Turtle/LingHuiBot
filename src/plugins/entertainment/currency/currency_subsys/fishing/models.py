from typing import Optional

from nonebot_plugin_orm import Model
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users


# ==================== ORM 表定义 ====================

class FishingData(Model):
    """玩家装备背包：鱼竿 + 鱼钩"""
    __tablename__ = "fishing_data"

    user_id: Mapped[str] = mapped_column(
        ForeignKey(Users.id), primary_key=True
    )
    fish_rod: Mapped[str] = mapped_column(
        String, default="basic_fishing_rod"
    )
    fish_hook: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default=None  # 初始无鱼钩，需单独购买
    )
    hook_durability: Mapped[int] = mapped_column(
        default=0  # 购买鱼钩时写入耐久
    )


class FishingBaitData(Model):
    __tablename__ = "fishing_bait"

    user_id: Mapped[str] = mapped_column(
        ForeignKey(Users.id), primary_key=True
    )
    basic_bait: Mapped[int] = mapped_column(BigInteger, default=5)
    intermediate_bait: Mapped[int] = mapped_column(BigInteger, default=0)
    advanced_bait: Mapped[int] = mapped_column(BigInteger, default=0)
    maximal_bait: Mapped[int] = mapped_column(BigInteger, default=0)


class FishingState(Model):
    __tablename__ = "fishing_state"

    user_id: Mapped[str] = mapped_column(
        ForeignKey(Users.id), primary_key=True
    )
    is_fishing: Mapped[bool] = mapped_column(Boolean, default=False)
    lure_end_time: Mapped[float] = mapped_column(Float, default=0.0)  # 溜鱼结束时间
    earliest_pull: Mapped[float] = mapped_column(Float, default=0.0)  # 最早收竿时间
    latest_pull: Mapped[float] = mapped_column(Float, default=0.0)  # 最晚收竿时间
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # 提醒是否已发
    base_wait: Mapped[int] = mapped_column(default=0)  # 本次随机基础等待秒数
    window_bonus: Mapped[int] = mapped_column(default=0)  # 本次鱼竿窗口加成


# ==================== 内存锁（防止同一用户并发触发竞态）====================

_fishing_lock: set[str] = set()


# ==================== 查询操作 ====================

async def get_fishing_data(session: AsyncSession, user_id: str) -> type[FishingData] | None:
    return await session.get(FishingData, user_id)


async def get_state(session: AsyncSession, user_id: str) -> type[FishingState] | None:
    return await session.get(FishingState, user_id)


async def get_bait(session: AsyncSession, user_id: str) -> type[FishingBaitData] | None:
    return await session.get(FishingBaitData, user_id)

async def get_hook(session,user_id:str) -> str | None:
    data = await session.get(FishingData, user_id)
    if data is None:
        return data
    return data.fish_hook

async def get_rod(session,user_id:str) -> str | None:
    data = await session.get(FishingData, user_id)
    if data is None:
        return data
    return data.fish_rod


# ==================== 初始化 ====================

async def init_player(session: AsyncSession, user_id: str) -> None:
    """
    初始化新玩家，创建三张表的对应行。
    调用前请确认该 user_id 尚未初始化，否则会触发主键冲突。
    Args:
        session: session数据库会话
        user_id: 用户QQ号
    Returns:
        None
    """
    has_data = await session.get(FishingData, user_id)
    has_bait = await session.get(FishingBaitData, user_id)
    has_state = await session.get(FishingState, user_id)

    if has_data is None:
        session.add(FishingData(user_id=user_id))

    if has_bait is None:
        session.add(FishingBaitData(user_id=user_id))

    if has_state is None:
        session.add(FishingState(user_id=user_id))
    await session.commit()


# ==================== 装备操作 ====================

async def equip_rod(session, user_id: str, rod_key: str) -> None:
    """
    更新玩家鱼竿。
    rod_key 对应 items.py 中 FishingRod 的属性名，如 "intermediate_fishing_rod"。
    """
    data = await get_fishing_data(session, user_id)
    if data is None:
        await init_player(session, user_id)
        data = await get_fishing_data(session, user_id)
    data.fish_rod = rod_key
    await session.commit()


async def equip_hook(
        session,
        user_id: str,
        hook_key: str,
        durability: int
) -> None:
    """
    更新玩家鱼钩并写入初始耐久。
    hook_key 对应 items.py 中 FishingHook 的属性名，如 "advanced_fishhook"。
    """
    data = await get_fishing_data(session, user_id)
    if data is None:
        await init_player(session, user_id)
        data = await get_fishing_data(session, user_id)
    data.fish_hook = hook_key
    data.hook_durability = durability
    await session.commit()


async def reduce_hook_durability(
        session: AsyncSession,
        user_id: str,
        amount: int = 1
) -> bool:
    """
    扣除鱼钩耐久，耐久归零时自动卸下鱼钩。
    返回 True 表示鱼钩仍可用，False 表示已损坏被卸下。
    """
    data = await get_fishing_data(session, user_id)
    data.hook_durability -= amount
    if data.hook_durability <= 0:
        data.fish_hook = None
        data.hook_durability = 0
        await session.commit()
        return False
    await session.commit()
    return True


# ==================== 饵料操作 ====================

BAIT_COLUMNS = {
    "basic": "basic_bait",
    "intermediate": "intermediate_bait",
    "advanced": "advanced_bait",
    "maximal": "maximal_bait",
}


async def add_bait(
        session: AsyncSession,
        user_id: str,
        bait_type: str,
        amount: int
) -> None:
    """
    增加饵料。bait_type 取 "basic" / "intermediate" / "advanced" / "maximal"。
    """
    col = BAIT_COLUMNS[bait_type]
    bait = await get_bait(session, user_id)
    setattr(bait, col, getattr(bait, col) + amount)
    await session.commit()


async def consume_bait(
        session: AsyncSession,
        user_id: str,
        bait_type: str = "basic"
) -> bool:
    """
    消耗一个饵料。库存不足时返回 False，消耗成功返回 True。
    """
    col = BAIT_COLUMNS[bait_type]
    bait = await get_bait(session, user_id)
    current = getattr(bait, col)
    if current < 1:
        return False
    setattr(bait, col, current - 1)
    await session.commit()
    return True


# ==================== 钓鱼状态操作 ====================

async def try_start_fishing(
        session: AsyncSession,
        user_id: str,
        lure_end_time: float,
        base_wait: int,
        window_bonus: int,
) -> bool:
    """
    尝试开始钓鱼。
    内存锁拦截极短时间内的重复触发；
    数据库层再校验 is_fishing 防止状态异常。
    返回 True 表示成功抛竿，False 表示已在钓鱼中。

    用法示例：
        success = await try_start_fishing(session, user_id, lure_end, base, bonus)
        if not success:
            await send("已在钓鱼中")
            return
    """
    if user_id in _fishing_lock:
        return False

    _fishing_lock.add(user_id)
    try:
        state = await get_state(session, user_id)
        if state.is_fishing:
            return False

        state.is_fishing = True
        state.lure_end_time = lure_end_time
        state.base_wait = base_wait
        state.window_bonus = window_bonus
        state.reminder_sent = False
        state.earliest_pull = 0.0
        state.latest_pull = 0.0
        await session.commit()
        return True
    finally:
        _fishing_lock.discard(user_id)


async def set_pull_window(
        session: AsyncSession,
        user_id: str,
        earliest: float,
        latest: float,
) -> None:
    """
    溜鱼结束后写入收竿时间窗口，并标记提醒已发送。
    在发送提竿提醒的定时回调里调用。
    """
    state = await get_state(session, user_id)
    state.earliest_pull = earliest
    state.latest_pull = latest
    state.reminder_sent = True
    await session.commit()


async def end_fishing(session: AsyncSession, user_id: str) -> None:
    """
    收竿后重置钓鱼状态（无论成功/太早/太晚均调用）。
    """
    state = await get_state(session, user_id)
    state.is_fishing = False
    state.reminder_sent = False
    state.earliest_pull = 0.0
    state.latest_pull = 0.0
    state.lure_end_time = 0.0
    state.base_wait = 0
    state.window_bonus = 0
    await session.commit()


async def process_fishing(session, user_id: str):
    """所有数据库读写和判断逻辑，作为内部使用事务"""
    fishing_data = await get_fishing_data(session, user_id)
    if fishing_data is None:
        await init_player(session, user_id)
        fishing_data = await get_fishing_data(session, user_id)
    fishing_state = await get_state(session, user_id)
    bait_data = await get_bait(session, user_id)
    result = False
    if not fishing_data.fish_hook:
        result = "你还没有购买鱼钩呢qwq"
    elif fishing_data.hook_durability == 0:
        result = "你的鱼钩好像损坏了呢qwq"
    elif bait_data.basic_bait == 0 and bait_data.intermediate_bait == 0 and bait_data.advanced_bait == 0 and bait_data.maximal_bait == 0:
        result = "你没有足够的饵料了呢qwq"
    elif fishing_state.is_fishing:
        result = "你已经在钓鱼了哦qwq"
    return result