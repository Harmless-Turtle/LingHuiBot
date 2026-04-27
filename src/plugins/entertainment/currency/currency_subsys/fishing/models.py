from typing import Optional
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_orm import Model

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
        String, nullable=True, default=None        # 初始无鱼钩，需单独购买
    )
    hook_durability: Mapped[int] = mapped_column(
        default=0                                  # 购买鱼钩时写入耐久
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
    lure_end_time: Mapped[float] = mapped_column(Float, default=0.0)   # 溜鱼结束时间
    earliest_pull: Mapped[float] = mapped_column(Float, default=0.0)   # 最早收竿时间
    latest_pull: Mapped[float] = mapped_column(Float, default=0.0)     # 最晚收竿时间
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False) # 提醒是否已发
    base_wait: Mapped[int] = mapped_column(default=0)                  # 本次随机基础等待秒数
    window_bonus: Mapped[int] = mapped_column(default=0)               # 本次鱼竿窗口加成

