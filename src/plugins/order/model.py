from datetime import datetime
from typing import Optional

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import DateTime, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .exceptions import OrderItemNotFoundError, OrderMenuEmptyError
from ..database.models import Users


class OrderItem(Model):
    """饮品/菜品数据模型"""

    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    picture_path: Mapped[str] = mapped_column(String(1024))
    uploader_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey(Users.id), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=True
    )


async def get_random_order_item(
        session: async_scoped_session,
) -> OrderItem:
    """随机获取一份饮品/菜品；没有数据时抛出 OrderMenuEmptyError"""
    result = await session.execute(
        select(OrderItem).order_by(func.random()).limit(1)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise OrderMenuEmptyError()
    return item


async def get_order_item_by_name(
        session: async_scoped_session, name: str
) -> Optional[OrderItem]:
    """根据名称查询饮品/菜品"""
    result = await session.execute(
        select(OrderItem).where(OrderItem.name == name)
    )
    return result.scalar_one_or_none()


async def add_or_update_order_item(
        session: async_scoped_session,
        name: str,
        picture_path: str,
        uploader_id: Optional[str] = None,
) -> OrderItem:
    """添加或更新饮品/菜品对象到 session（不进行 commit）"""
    item = await get_order_item_by_name(session, name)
    if item is None:
        item = OrderItem(
            name=name,
            picture_path=picture_path,
            uploader_id=uploader_id,
            created_at=datetime.now(),
        )
        session.add(item)
    else:
        item.picture_path = picture_path
        if uploader_id is not None:
            item.uploader_id = uploader_id

    return item


async def delete_order_item(
        session: async_scoped_session, name: str
) -> str:
    """删除指定名称的饮品/菜品；若不存在则抛出 OrderItemNotFoundError。返回旧图片路径以便外部清理"""
    item = await get_order_item_by_name(session, name)
    if item is None:
        raise OrderItemNotFoundError(name)

    pic_path = item.picture_path
    await session.delete(item)
    return pic_path


async def get_all_order_items(
        session: async_scoped_session,
) -> list[OrderItem]:
    """获取所有饮品/菜品列表"""
    result = await session.execute(select(OrderItem))
    return list(result.scalars().all())
