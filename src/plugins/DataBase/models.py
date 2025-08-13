# plugins/sql_tool/models.py
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 读取 NoneBot 全局配置
from nonebot import get_driver
config = get_driver().config

# 如果 `nb run` 已经设置了环境变量可直接用，否则给个默认值
DATABASE_URL = getattr(config, "mysql_url", None)
if not DATABASE_URL:
    raise ValueError("请在 NoneBot 配置中设置 mysql_url")

# SQLAlchemy 基础
Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Item(Base):
    """示例表：可自由扩展字段"""
    __tablename__ = "items"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    data = Column(Text, nullable=True)

    @staticmethod
    def create(name: str, data: Optional[str] = None) -> "Item":
        with SessionLocal() as db:
            item = Item(name=name, data=data)
            db.add(item)
            db.commit()
            db.refresh(item)
            return item

    @staticmethod
    def get(pk: int) -> Optional["Item"]:
        with SessionLocal() as db:
            return db.get(Item, pk)

    @staticmethod
    def list_all() -> List["Item"]:
        with SessionLocal() as db:
            return db.query(Item).all()

    def update(self, **kwargs) -> "Item":
        with SessionLocal() as db:
            for k, v in kwargs.items():
                setattr(self, k, v)
            db.merge(self)
            db.commit()
            db.refresh(self)
            return self

    def delete(self) -> None:
        with SessionLocal() as db:
            db.delete(self)
            db.commit()

# 首次运行自动建表
Base.metadata.create_all(bind=engine)

__all__ = ['Item', 'SessionLocal', 'engine', 'Base']