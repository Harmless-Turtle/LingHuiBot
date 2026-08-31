from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column


class Users(Model):
    id: Mapped[str] = mapped_column(primary_key=True)


class Groups(Model):
    id: Mapped[str] = mapped_column(primary_key=True)


# ============================================================
#                     通用背包（共享模型）
#   item_id 形如 seed_wheat（种子）/ wheat（产物）/ bait（饵料）
#   被 种地(farm) 与 钓鱼(fishing) 等多个系统共用，
#   因此作为共享模型保留在 database 模块
# ============================================================

class Inventory(Model):
    """通用背包：item_id 形如 seed_wheat（种子）/ wheat（产物）/ bait（饵料）。"""
    __tablename__ = "inventory"
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    item_id: Mapped[str] = mapped_column(String, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# ---------------- 通用背包 ----------------

async def add_inventory(
        session: async_scoped_session, user_id: str, item_id: str, qty: int = 1
) -> None:
    if qty <= 0:
        return
    res = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        session.add(Inventory(user_id=user_id, item_id=item_id, quantity=qty))
    else:
        row.quantity += qty
    await session.flush()


async def get_inventory_qty(
        session: async_scoped_session, user_id: str, item_id: str
) -> int:
    res = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id,
        )
    )
    row = res.scalar_one_or_none()
    return row.quantity if row is not None else 0


async def remove_inventory(
        session: async_scoped_session, user_id: str, item_id: str, qty: int = 1
) -> bool:
    """从背包扣除 qty 个物品，不足则返回 False 且不扣。"""
    if qty <= 0:
        return True
    res = await session.execute(
        select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id,
        )
    )
    row = res.scalar_one_or_none()
    if row is None or row.quantity < qty:
        return False
    row.quantity -= qty
    if row.quantity == 0:
        await session.delete(row)
    await session.flush()
    return True
