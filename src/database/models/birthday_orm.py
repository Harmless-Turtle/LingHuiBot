from nonebot.adapters.onebot.v11 import GroupMessageEvent

__import__("nonebot").require("nonebot_plugin_orm")
from datetime import datetime, date, timedelta
from typing import Annotated

from nonebot.params import Depends
from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import Date, DateTime, ForeignKey, select, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models.core_models import get_user_id, get_group_id


class GroupSettings(Model):
    __tablename__ = "group_settings"

    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    enable: Mapped[bool] = mapped_column(default=False)
    last_reply_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(Model):
    __tablename__ = "user_profile"

    user_id: Annotated[Mapped[str], Depends(get_user_id)] = mapped_column(ForeignKey("users.id"), primary_key=True)
    birthday_date: Mapped[date | None] = mapped_column(Date(), nullable=True)


class UserGroupUsage(Model):
    __tablename__ = "user_group_usage"

    user_id: Annotated[Mapped[str], Depends(get_user_id)] = mapped_column(ForeignKey("users.id"), primary_key=True)
    group_id: Annotated[Mapped[str], Depends(get_group_id)] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date(), primary_key=True)
    usage_count: Mapped[int] = mapped_column(default=0)


async def inc_user_group_usage_today(session: async_scoped_session, event: GroupMessageEvent, ) -> None:
    user_id = str(event.user_id)
    group_id = str(event.group_id)

    today = date.today()
    result = await session.execute(
        select(UserGroupUsage).where(
            UserGroupUsage.user_id == user_id,
            UserGroupUsage.group_id == group_id,
            UserGroupUsage.day == today,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        obj = UserGroupUsage(user_id=user_id, group_id=group_id, day=today, usage_count=1)
        session.add(obj)
    else:
        obj.usage_count += 1
    session.commit()


async def get_user_group_usage_last_7_days(session: async_scoped_session, event: GroupMessageEvent) -> int:
    user_id = str(event.user_id)
    group_id = str(event.group_id)

    since = date.today() - timedelta(days=6)
    result = await session.execute(
        select(func.coalesce(func.sum(UserGroupUsage.usage_count), 0)).where(
            UserGroupUsage.user_id == user_id,
            UserGroupUsage.group_id == group_id,
            UserGroupUsage.day >= since,
        )
    )
    return int(result.scalar_one())

async def get_or_create_group_settings(session: async_scoped_session, event: GroupMessageEvent):
    group_id = str(event.group_id)
    if (obj := await session.get(GroupSettings, group_id)) is None:
        obj = GroupSettings(group_id=group_id, enable=False)

    try:
        yield obj
    finally:
        session.add(obj)
        await session.commit()
