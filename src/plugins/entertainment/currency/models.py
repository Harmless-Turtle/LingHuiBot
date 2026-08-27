from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, BigInteger, select
from sqlalchemy.orm import Mapped, mapped_column

from .exceptions import CurrencyBalanceNotEnough, CurrencyInvalidAmount
from ...database.models import Users

MAX_MOHUI_COIN = 9223372036854775807


class MoHuiCoinData(Model):
    __tablename__ = "MHCoin_data"
    # 外键关联 Users 表，作为主键
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    # 金币数量，必须是整数，默认为 0
    mohui_coin: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)


async def add_mohui_coin(session, user_id: str, amount: int) -> int:
    if amount <= 0:
        raise CurrencyInvalidAmount()

    obj = await get_mohui_data(session, user_id)

    if obj is None:
        obj = MoHuiCoinData(user_id=user_id, mohui_coin=0)
        session.add(obj)
        await session.flush()

    obj.mohui_coin += amount
    await session.flush()

    return obj.mohui_coin


async def remove_mohui_coin(session, user_id: str, amount: int) -> int:
    """
    Args:
        session:Session数据库会话
        user_id: 要操作的用户QQ号
        amount: 要操作的金额数字

    Returns:
        int: 操作后的墨辉币余额
    """
    if amount <= 0:
        raise CurrencyInvalidAmount()

    obj = await get_mohui_data(session, user_id)

    if obj is None:
        obj = MoHuiCoinData(user_id=user_id, mohui_coin=0)
        session.add(obj)
        await session.flush()
        raise CurrencyBalanceNotEnough()

    if obj.mohui_coin < amount:
        raise CurrencyBalanceNotEnough()

    obj.mohui_coin -= amount
    await session.flush()

    return obj.mohui_coin


async def get_mohui_data(session: async_scoped_session, user_id: str) -> MoHuiCoinData:
    """获取用户的墨辉币记录；若记录不存在则自动创建并初始化为 0。"""
    result = await session.execute(
        select(MoHuiCoinData)
        .where(MoHuiCoinData.user_id == user_id)
    )
    coin = result.scalar_one_or_none()

    if coin is None:
        coin = MoHuiCoinData(user_id=user_id, mohui_coin=0)
        session.add(coin)
        await session.flush()

    return coin
