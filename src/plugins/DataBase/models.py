from typing import Optional, Type
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from nonebot import get_driver
config = get_driver().config

DATABASE_URL = getattr(config, "mysql_url", None)
if not DATABASE_URL:
    raise ValueError("请在 NoneBot 配置中设置 mysql_url")

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def create_item_model(tablename: str = "items") -> Type:
    class Item(Base):
        __tablename__ = tablename
        __table_args__ = {'extend_existing': True}  # 允许重复定义表

        id    = Column(Integer, primary_key=True, index=True)
        name  = Column(String(64), unique=True, nullable=False)
        data  = Column(Text, nullable=True)
        count = Column(Integer, default=0, nullable=False)
        

        @staticmethod
        def create(name: str, data: Optional[str] = None, count: int = 0) -> "Item":
            with SessionLocal() as db:
                exists = db.query(Item).filter_by(name=name).first()
                if exists:
                    raise ValueError(f"name 应是唯一值，而它现在已存在于表 {name} 中。")
                obj = Item(name=name, data=data, count=count)
                db.add(obj)
                db.commit()
                db.refresh(obj)
                return obj

        def save(self) -> "Item":
            with SessionLocal() as db:
                db.merge(self)
                db.commit()
                db.refresh(self)
                return self

        def delete(self) -> None:
            with SessionLocal() as db:
                db.delete(self)
                db.commit()

    return Item

__all__ = ['create_item_model', 'SessionLocal', 'engine', 'Base']