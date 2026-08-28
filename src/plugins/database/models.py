from typing import Optional

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import BigInteger, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column


class Users(Model):
    id: Mapped[str] = mapped_column(primary_key=True)


class Groups(Model):
    id: Mapped[str] = mapped_column(primary_key=True)


# ============================================================
#                     种地 & 钓鱼系统
#   farm_plot / inventory / fishing_session
# ============================================================

class FarmPlot(Model):
    """种地地块：每 (user, plot_index) 一行；crop_id 为空表示空闲。"""
    __tablename__ = "farm_plot"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    plot_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 已种植作物 id（如 wheat）；None 表示空闲
    crop_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # 种植时刻（epoch 秒）；None 表示空闲
    planted_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class Inventory(Model):
    """通用背包：item_id 形如 seed_wheat（种子）/ wheat（产物）/ bait（饵料）。"""
    __tablename__ = "inventory"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    item_id: Mapped[str] = mapped_column(String, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FishingSession(Model):
    """钓鱼会话与装备状态：每 user 一行；state 为空表示当前未在钓鱼。"""
    __tablename__ = "fishing_session"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    # 抛竿所在群，用于定时推送"鱼上钩"
    group_id: Mapped[str] = mapped_column(String, default="", nullable=False)
    # 装备：鱼竿 id（如 carbon_standard）与剩余耐久；鱼钩 id（如 gold）
    rod_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rod_durability: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hook_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # 会话状态："fishing" 表示正在钓鱼；None 表示空闲
    state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cast_at: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # 上钩时刻（推送"鱼上钩"）；溜鱼结束=窗口开启；窗口关闭
    bite_at: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    window_start: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    window_end: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # 本次结果：fish:<tier_id> / item:chest / item:junk / item:badluck
    outcome: Mapped[str] = mapped_column(String, default="", nullable=False)


# ---------------- 通用背包 ----------------

async def add_inventory(
        session: async_scoped_session, user_id: str, item_id: str, qty: int = 1
) -> None:
    if qty <= 0:
        return
    res = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        session.add(Inventory(user_id=user_id, item_id=item_id, quantity=qty))
    else:
        row.quantity += qty
    await session.flush()


async def get_inventory_qty(
        session: async_scoped_session, user_id: str, item_id: str
) -> int:
    res = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id,
        )
    )
    row = res.scalar_one_or_none()
    return row.quantity if row is not None else 0


async def remove_inventory(
        session: async_scoped_session, user_id: str, item_id: str, qty: int = 1
) -> bool:
    """从背包扣除 qty 个物品，不足则返回 False 且不扣。"""
    if qty <= 0:
        return True
    res = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id,
        )
    )
    row = res.scalar_one_or_none()
    if row is None or row.quantity < qty:
        return False
    row.quantity -= qty
    if row.quantity == 0:
        await session.delete(row)
    await session.flush()
    return True


# ---------------- 种地 ----------------

async def get_farm_plots(
        session: async_scoped_session, user_id: str
) -> list[FarmPlot]:
    res = await session.execute(
        select(FarmPlot)
        .where(FarmPlot.user_id == user_id)
        .order_by(FarmPlot.plot_index)
    )
    return list(res.scalars())


async def get_farm_plot(
        session: async_scoped_session, user_id: str, plot_index: int
) -> Optional[FarmPlot]:
    res = await session.execute(
        select(FarmPlot).where(
            FarmPlot.user_id == user_id,
            FarmPlot.plot_index == plot_index,
        )
    )
    return res.scalar_one_or_none()


async def add_farm_plot(
        session: async_scoped_session, user_id: str
) -> FarmPlot:
    plots = await get_farm_plots(session, user_id)
    index = (plots[-1].plot_index + 1) if plots else 1
    plot = FarmPlot(user_id=user_id, plot_index=index, crop_id=None, planted_at=None)
    session.add(plot)
    await session.flush()
    return plot


async def plant_crop(
        session: async_scoped_session, user_id: str, plot_index: int,
        crop_id: str, now_ts: int,
) -> bool:
    plot = await get_farm_plot(session, user_id, plot_index)
    if plot is None or plot.crop_id is not None:
        return False
    plot.crop_id = crop_id
    plot.planted_at = now_ts
    await session.flush()
    return True


async def clear_farm_plot(
        session: async_scoped_session, user_id: str, plot_index: int
) -> Optional[FarmPlot]:
    plot = await get_farm_plot(session, user_id, plot_index)
    if plot is None:
        return None
    plot.crop_id = None
    plot.planted_at = None
    await session.flush()
    return plot


# ---------------- 钓鱼 ----------------

async def get_fishing_session(
        session: async_scoped_session, user_id: str
) -> FishingSession:
    res = await session.execute(
        select(FishingSession).where(FishingSession.user_id == user_id)
    )
    row = res.scalar_one_or_none()
    if row is None:
        row = FishingSession(user_id=user_id)
        session.add(row)
        await session.flush()
    return row

