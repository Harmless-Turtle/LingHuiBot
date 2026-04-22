from datetime import date

from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database.models import Users, Groups


class UserBirthdayData(Model):
    __tablename__ = "birthday_data"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    birthday_date: Mapped[date | str |None] = mapped_column(Date(), nullable=True)
    group_id: Mapped[int] = mapped_column(ForeignKey(Groups.id), nullable=True,primary_key=True)

class GroupSettings(Model):
    __tablename__ = "group_settings"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    enable: Mapped[bool] = mapped_column(default=False)


async def get_group_settings(session: async_scoped_session,event: GroupMessageEvent):
    group_id = str(event.group_id)
    obj = await session.get(GroupSettings, group_id)
    if obj is None:
        obj = GroupSettings(group_id=group_id, enable=False)
    try:
        yield obj
    finally:
        session.add(obj)
        await session.commit()

async def get_user_birthday(session: async_scoped_session, event: GroupMessageEvent):
    user_id = str(event.user_id)
    obj = await session.get(UserBirthdayData, user_id)
    if obj is None:
        obj = UserBirthdayData(user_id=user_id)

    try:
        yield obj
    finally:
        session.add(obj)
        await session.commit()

async def delete_user_birthday(session: async_scoped_session, event: GroupMessageEvent) -> bool:
    user_id = str(event.user_id)
    obj = await session.get(UserBirthdayData, user_id)
    if obj is None or obj.birthday_date is None:
        return False
    await session.delete(obj)
    await session.commit()
    return True
