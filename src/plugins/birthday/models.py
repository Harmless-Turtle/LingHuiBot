from datetime import datetime, date

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import Date, DateTime, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users, Groups


class GroupSettings(Model):
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    enable: Mapped[bool] = mapped_column(default=False)
    last_reply_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class UserBirthday(Model):
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    birthday_date: Mapped[date | None] = mapped_column(Date(), nullable=True)


class UserGroupUsage(Model):
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    day: Mapped[date] = mapped_column(Date(), primary_key=True)
    usage_count: Mapped[int] = mapped_column(default=0)


async def inc_user_group_usage_today(session: async_scoped_session, event: GroupMessageEvent) -> None:
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
    await session.commit()


async def get_or_create_group_settings(session: async_scoped_session, event: GroupMessageEvent):
    group_id = str(event.group_id)
    obj = await session.get(GroupSettings, group_id)
    if obj is None:
        obj = GroupSettings(group_id=group_id, enable=False)

    try:
        yield obj
    finally:
        session.add(obj)
        await session.commit()


async def get_or_create_user_birthday(session: async_scoped_session, event: GroupMessageEvent):
    user_id = str(event.user_id)
    obj = await session.get(UserBirthday, user_id)
    if obj is None:
        obj = UserBirthday(user_id=user_id)

    try:
        yield obj
    finally:
        session.add(obj)
        await session.commit()


async def delete_user_birthday(session: async_scoped_session, event: GroupMessageEvent) -> bool:
    user_id = str(event.user_id)
    obj = await session.get(UserBirthday, user_id)
    if obj is None or obj.birthday_date is None:
        return False
    await session.delete(obj)
    await session.commit()
    return True
