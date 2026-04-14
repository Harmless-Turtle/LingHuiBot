from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users


MAX_MOHUI_COIN = 9223372036854775807
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
        await session.refresh(obj)

    return int(str(obj.mohui_coin))


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
        result = obj.mohui_coin + amount
        if result > MAX_MOHUI_COIN:
            raise ValueError(f"操作失败，墨辉币余额不能超过 {MAX_MOHUI_COIN} 个")
        obj.mohui_coin += amount

    await session.commit()
    await session.refresh(obj)
    return obj.mohui_coin