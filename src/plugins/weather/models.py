from nonebot_plugin_orm import Model
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Groups


class TyphoonSubscribe(Model):
    __tablename__ = "Typhoon_Subscribe"
    # 群号
    group_id: Mapped[int] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    # 是否开启随机漂流
    enable: Mapped[bool] = mapped_column(default=False, nullable=True)


async def add_typhoon_sub(session:AsyncSession, group_id: int) -> TyphoonSubscribe:
    """
    获取或创建台风订阅配置。
    """
    subscribe = await session.get(TyphoonSubscribe, group_id)
    if subscribe is None:
        subscribe = TyphoonSubscribe(group_id=group_id, enable=False)
        session.add(subscribe)
        await session.commit()
        await session.refresh(subscribe)
    return subscribe