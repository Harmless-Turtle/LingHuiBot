from typing import Optional

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import BigInteger, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..database.models import Users


# ============================================================
#                       钓鱼系统
#   fishing_session 表 + 会话 CRUD（通用背包 inventory 见 database.models）
# ============================================================

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
