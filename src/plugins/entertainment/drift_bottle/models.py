from datetime import date

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users, Groups


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


async def add_drift_bottle(session: async_scoped_session, user_id: str, group_id: str, drift_bottle_data: str):
    """
    添加用户抛出的漂流瓶在数据库中作为备份
    """
    new_bottle = DriftBottleModel(
        user_id=user_id,
        data=drift_bottle_data,
        time=date.today(),
        group_id=group_id
    )
    session.add(new_bottle)
    await session.commit()
