from datetime import datetime
from typing import Optional

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ...database.models import Users


# ============================================================
#                       种地系统
#   farm_plot 表 + 地块 CRUD（通用背包 inventory 见 database.models）
# ============================================================

class FarmPlot(Model):
    """种地地块：每 (user, plot_index) 一行；crop_id 为空表示空闲。"""
    __tablename__ = "farm_plot"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    plot_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 已种植作物 id（如 wheat）；None 表示空闲
    crop_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # 种植时刻：标准 UTC（naive datetime）；None 表示空闲
    planted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)


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
        crop_id: str, now: datetime,
) -> bool:
    plot = await get_farm_plot(session, user_id, plot_index)
    if plot is None or plot.crop_id is not None:
        return False
    plot.crop_id = crop_id
    plot.planted_at = now
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
