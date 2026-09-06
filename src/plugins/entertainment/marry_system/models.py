import enum
from datetime import datetime
from typing import Optional

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, select, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ...database.models import Groups, Users


class MarryMode(enum.Enum):
    """婚姻/求婚状态：统一 ORM 与业务层的类型。"""
    SINGLE = "single"  # 单身/无对象
    ACTIVE_PROPOSE = "active_propose"  # 主动求婚中
    PASSIVE_PROPOSE = "passive_propose"  # 被求婚中
    MARRIED = "married"  # 已婚


# ============================================================
#                       结婚系统
#   原 data/entertainment/marry_system/marry.json
#   结构：data[user][group] = {cp_qq, time, request, request_mode, count, switch}
#   迁移为每 (user, group) 一行；
# ============================================================


class MarryRecord(Model):
    __tablename__ = "marry_record"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    # 对象 QQ；仅已婚(MARRIED)时为对象 QQ，否则为 0
    cp_qq: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # 求婚目标 QQ；求婚中(ACTIVE/PASSIVE_PROPOSE)生效，否则为 0
    request: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    # 婚姻/求婚状态（MarryMode 枚举）：SQLAlchemy Enum 自动转换
    request_mode: Mapped[MarryMode] = mapped_column(Enum(MarryMode), default=MarryMode.SINGLE)
    # 结婚/求婚时间：标准 UTC（naive datetime），业务层按需 +8 小时转本地
    time: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    # “换老婆”功能的当日计数与免打扰开关
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    switch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


async def get_marry_record(
        session: async_scoped_session, user_id: str, group_id: str
) -> Optional[MarryRecord]:
    res = await session.execute(
        select(MarryRecord).where(
            MarryRecord.user_id == user_id,
            MarryRecord.group_id == group_id,
        )
    )
    return res.scalar_one_or_none()


async def get_or_create_marry_record(
        session: async_scoped_session, user_id: str, group_id: str
) -> MarryRecord:
    rec = await get_marry_record(session, user_id, group_id)
    if rec is None:
        rec = MarryRecord(user_id=user_id, group_id=group_id)
        session.add(rec)
        await session.flush()
    return rec


async def delete_marry_record(
        session: async_scoped_session, user_id: str, group_id: str
) -> None:
    rec = await get_marry_record(session, user_id, group_id)
    if rec is not None:
        await session.delete(rec)
        await session.flush()


async def get_partnered_user_ids_in_group(
        session: async_scoped_session, group_id: str
) -> list[str]:
    """
    返回该群中已有对象或正在求婚（request_mode != SINGLE）的 user_id 列表，
    等价于原 marry_switch 中构建排除列表的逻辑。
    """
    res = await session.execute(
        select(MarryRecord.user_id).where(
            MarryRecord.group_id == group_id,
            MarryRecord.request_mode != MarryMode.SINGLE,
        )
    )
    return [row[0] for row in res.all()]
