from nonebot_plugin_orm import Model, AsyncSession
from sqlalchemy import ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users
from src.plugins.entertainment.currency.models import MoHuiCoinData

class BankCoinData(Model):
    __tablename__ = "BankCoin_data"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    bank_coin: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

async def get_bank_coin(session: AsyncSession, user_id: str) -> int:
    """
        获取用户银行墨辉币余额的函数。
    Args:
        session: SQLAlchemy session
        user_id: 用户id

    Returns:
        用户银行墨辉币余额的整数值
    """
    bank_obj = await session.get(BankCoinData, user_id)
    if bank_obj is None:
        return 0
    return int(str(bank_obj.bank_coin))

async def bank_operation(
        session: AsyncSession,
        user_id: str,
        amount: int,
        operation: str = "save"
) -> str:
    """
        银行操作函数，支持存款和取款两种操作。
    Args:
        session: SQLAlchemy session
        user_id: 操作的用户id
        amount: 操作的金额数量
        operation: 操作类型，"save"表示存款，"remove"表示取款

    Returns:
        操作结果的字符串描述
    """
    # 判断数字是否合法
    if amount <= 0: return "操作金额必须大于0"
    # 获取数据，如果不存在则在内存中实例化
    work_capital_obj = await session.get(MoHuiCoinData, user_id) or MoHuiCoinData(user_id=user_id, mohui_coin=0)
    bank_obj = await session.get(BankCoinData, user_id) or BankCoinData(user_id=user_id, bank_coin=0)

    # 如果是新实例，添加到 session
    if work_capital_obj not in session: session.add(work_capital_obj)
    if bank_obj not in session: session.add(bank_obj)
    # 获取想要执行的状态
    # 存款操作
    if operation == "save":
        # 判断墨辉币余额是否充足
        if work_capital_obj.mohui_coin < amount:
            return "操作失败，墨辉币余额不足"
        # 操作用户数据
        work_capital_obj.mohui_coin -= amount
        bank_obj.bank_coin += amount
        return f"操作成功完成，存入银行{amount}个墨辉币，目前银行余额为{bank_obj.bank_coin}个墨辉币"
    # 取款操作
    elif operation == "remove":
        # 判断墨辉币余额是否充足
        if bank_obj.bank_coin < amount:
            return "操作失败，墨辉币余额不足"
        # 操作用户数据
        work_capital_obj.mohui_coin += amount
        bank_obj.bank_coin -= amount
        return f"操作成功完成，从银行取出了{amount}个墨辉币，目前银行余额为{bank_obj.bank_coin}个墨辉币。"
    else:
        return "操作失败，未知的操作类型，请使用'save'或'remove'作为操作类型。"


async def transfer_money(
        session: AsyncSession,
        user_id: str,
        to_user_id: str,
        amount: int
) -> str:
    """
        转账函数，将指定金额的墨辉币从一个用户转账给另一个用户。
    Args:
        session: SQLAlchemy session
        user_id: 主动操作的用户id
        to_user_id:被动操作的用户id
        amount:操作的金额

    Returns:
        操作结果的字符串描述
    """
    # 判断数字是否合法
    if amount <= 0:
        return "操作金额必须大于0"
    # 获取数据，如果不存在则在内存中实例化
    user_obj = await session.get(BankCoinData, user_id) or BankCoinData(user_id=user_id, bank_coin=0)
    to_user_obj = await session.get(BankCoinData, to_user_id) or BankCoinData(user_id=to_user_id, bank_coin=0)
    # 如果是新实例，添加到 session
    if user_obj not in session: session.add(user_obj)
    if to_user_obj not in session: session.add(to_user_obj)
    if user_obj.bank_coin < amount:
        return "你的存款好像不足以转账呢qwq"
    user_obj.bank_coin -= amount
    to_user_obj.bank_coin += amount
    return "转账的操作成功了捏~"