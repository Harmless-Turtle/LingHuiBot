from datetime import date

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import Date, ForeignKey, String, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from .exceptions import DriftBottleError
from ...database.models import Users, Groups


class DriftBottleModel(Model):
    __tablename__ = "drift_bottle"
    # 新建自增式id来存储同一用户的多个漂流瓶数据
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 关联用户
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), nullable=False)
    # 关联群号
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), nullable=False)
    # 漂流瓶数据
    data: Mapped[str] = mapped_column(String, default=0, nullable=False)
    # 投掷时间
    time: Mapped[date | str | None] = mapped_column(Date(), nullable=True)


class DriftBottleGroupConfig(Model):
    __tablename__ = "drift_bottle_group_config"
    # 群号
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    # 是否开启随机漂流
    enable: Mapped[bool] = mapped_column(default=False, nullable=False)


async def add_drift_bottle(
        session: async_scoped_session,
        event: GroupMessageEvent,
        drift_bottle_data: str
):
    """添加用户抛出的漂流瓶在数据库中作为备份"""
    user_id = str(event.user_id)
    group_id = str(event.group_id)

    try:
        new_bottle = DriftBottleModel(
            user_id=user_id,
            data=drift_bottle_data,
            time=date.today(),
            group_id=group_id
        )
        session.add(new_bottle)
        await session.flush()

    except SQLAlchemyError as e:
        await session.rollback()
        raise DriftBottleError from e


async def get_random_drift_bottle(session: async_scoped_session | AsyncSession) -> DriftBottleModel | None:
    """随机获取一条漂流瓶，并将其从数据库中删除；没有数据时返回 None。"""
    try:
        result = await session.execute(
            select(DriftBottleModel)
            .order_by(func.random())
            .limit(1)
        )
        bottle = result.scalar_one_or_none()
        if bottle is None:
            return None

        await session.delete(bottle)
        await session.flush()
        return bottle

    except SQLAlchemyError as e:
        await session.rollback()
        raise DriftBottleError from e


async def get_or_create_drift_bottle_group_config(
        session: async_scoped_session | AsyncSession,
        group_id: str
) -> DriftBottleGroupConfig:
    """获取指定群的漂流瓶配置；若不存在则自动创建默认配置。"""
    try:
        result = await session.execute(
            select(DriftBottleGroupConfig)
            .where(DriftBottleGroupConfig.group_id == group_id)
        )
        config = result.scalar_one_or_none()
        if config is None:
            config = DriftBottleGroupConfig(group_id=group_id, enable=False)
            session.add(config)
            await session.flush()
        return config

    except SQLAlchemyError as e:
        await session.rollback()
        raise DriftBottleError from e


async def get_enabled_drift_bottle_group_ids(session: async_scoped_session | AsyncSession) -> list[str]:
    """获取所有开启随机漂流的群号。"""
    try:
        result = await session.execute(
            select(DriftBottleGroupConfig.group_id).where(DriftBottleGroupConfig.enable.is_(True))
        )
        return list(result.scalars().all())

    except SQLAlchemyError as e:
        await session.rollback()
        raise DriftBottleError from e
