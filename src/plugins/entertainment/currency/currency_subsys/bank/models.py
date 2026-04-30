from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, BigInteger, select
from sqlalchemy.orm import Mapped, mapped_column

from .exceptions import (
    InvalidBankOperation,
    BankBalanceNotEnough,
    InvalidTransferAmount,
    InvalidTransferTarget,
)
from ...models import MoHuiCoinData, Users


class BankCoinData(Model):
    __tablename__ = "BankCoin_data"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    bank_coin: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)


async def get_bank_data(session: async_scoped_session, user_id: str) -> BankCoinData:
    """获取用户的银行记录；若记录不存在则自动创建并初始化为 0。"""
    result = await session.execute(
        select(BankCoinData)
        .where(BankCoinData.user_id == user_id)
    )
    coin = result.scalar_one_or_none()

    if coin is None:
        coin = BankCoinData(user_id=user_id, bank_coin=0)
        session.add(coin)
        await session.flush()

    return coin


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


async def bank_operation(
        session: async_scoped_session,
        user_id: str,
        amount: int,
        operation: str
) -> BankCoinData:
    """
        执行银行余额变更操作。

        支持两种操作类型：

        - "save"：将指定数量的墨辉币存入银行，扣减墨辉币余额并增加银行余额。
        - "remove"：从银行取出指定数量的墨辉币，增加墨辉币余额并扣减银行余额。

        若余额不足或操作类型非法，则抛出对应异常。

    Raises:
        BankBalanceNotEnough: 当存款时墨辉币余额不足，或取款时银行余额不足。
        InvalidBankOperation: 当 `operation` 不是 "save" 或 "remove" 时。

    Args:
        session: SQLAlchemy session。
        user_id: 操作的用户 id。
        amount: 操作金额，必须为正整数。
        operation: 操作类型，"save" 表示存款，"remove" 表示取款。

    Returns:
        更新后的银行余额。
    """

    # 读取当前余额；不存在时会在查询函数中自动创建默认记录
    mohui_coin = await get_mohui_data(session, user_id)
    bank_coin = await get_bank_data(session, user_id)

    # 根据操作类型变更余额
    if operation == "save":
        # 存款前检查墨辉币余额是否充足
        if mohui_coin.mohui_coin < amount:
            raise BankBalanceNotEnough("")
        mohui_coin.mohui_coin -= amount
        bank_coin.bank_coin += amount
    elif operation == "remove":
        # 取款前检查银行余额是否充足
        if bank_coin.bank_coin < amount:
            raise BankBalanceNotEnough("")
        mohui_coin.mohui_coin += amount
        bank_coin.bank_coin -= amount
    else:
        raise InvalidBankOperation("")

    return bank_coin


async def transfer_money(
        session: async_scoped_session,
        user_id: str,
        target_user_id: str | None,
        amount: int
) -> BankCoinData:
    """
        转账函数，将指定金额的墨辉币从一个用户转账给另一个用户。
    Args:
        session: SQLAlchemy session
        user_id: 主动操作的用户id
        target_user_id: 被动操作的用户id
        amount: 操作的金额

    Raises:
        InvalidTransferTarget: 当转账目标不存在、尝试自转账或目标无效时
        InvalidTransferAmount: 当金额不合法时
        BankBalanceNotEnough: 当余额不足时
    """
    # 参数验证：检查转账目标是否存在
    if not target_user_id:
        raise InvalidTransferTarget("请在命令后艾特想要转账的用户哦~")

    # 参数验证：检查转账目标和源用户是否为同一人
    if user_id == target_user_id:
        raise InvalidTransferTarget("不能给自己转账哦！")

    # 参数验证：检查转账金额是否合法
    if amount <= 0:
        raise InvalidTransferAmount("请正确输入转账金额，例如：转账 @用户 100")

    # 获取双方的银行余额，不存在时会在查询函数中自动创建默认记录
    from_obj = await get_bank_data(session, user_id)
    target_obj = await get_bank_data(session, target_user_id)

    # 业务检查：检查转账方余额是否充足
    if from_obj.bank_coin < amount:
        raise BankBalanceNotEnough("你的存款好像不足以转账呢qwq")

    # 执行转账操作：更新两个用户的银行余额
    from_obj.bank_coin -= amount
    target_obj.bank_coin += amount

    await session.flush()
    return target_obj
