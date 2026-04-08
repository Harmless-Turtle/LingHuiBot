from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users



class MoHuiCoinData(Model):
    __tablename__ = "MHCoin_data"
    # 外键关联 Users 表，作为主键
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    # 金币数量，必须是整数，默认为 0
    mohui_coin: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


async def get_user_coin(session: async_scoped_session, user_id: str) -> int:
    """
    查询用户的墨辉币余额。如果用户不存在，则自动创建一条余额为 0 的记录。
    """
    obj = await session.get(MoHuiCoinData, user_id)
    if obj is None:
        # 如果数据库没这个人，就新建一个，初始金币为 0
        obj = MoHuiCoinData(user_id=user_id, mohui_coin=0)
        session.add(obj)
        await session.commit()

    return obj.mohui_coin


async def modify_user_coin(session: async_scoped_session, user_id: str, amount: int) -> int:
    """
    修改用户的墨辉币（增加或减少）。
    amount 为正数则是增加，为负数则是扣除。
    返回修改后的最新余额。
    """
    obj = await session.get(MoHuiCoinData, user_id)

    if obj is None:
        obj = MoHuiCoinData(user_id=user_id, mohui_coin=amount)
        session.add(obj)
    else:
        obj.mohui_coin += amount

    await session.commit()
    await session.refresh(obj)
    return obj.mohui_coin


async def delete_user_coin_record(session: async_scoped_session, user_id: str) -> bool:
    """
    删除用户的墨辉币记录（用于注销账号）。
    删除成功返回 True，如果没有该用户记录返回 False。
    """
    obj = await session.get(MoHuiCoinData, user_id)
    if obj is None:
        return False

    await session.delete(obj)
    await session.commit()
    return True