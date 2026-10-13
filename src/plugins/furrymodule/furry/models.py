from datetime import datetime
from pathlib import Path
import os

from nonebot_plugin_orm import Model,async_scoped_session
from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users, Groups


class FurryUploadRequest(Model):
    """投图审核队列（原 data/furry_system/upload/upload/manifest.json）"""
    __tablename__ = "furry_upload_request"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey(Users.id),nullable=True)
    group_id: Mapped[str | None] = mapped_column(ForeignKey(Groups.id), nullable=True)
    file_path: Mapped[str] = mapped_column(String,nullable=True)
    file_name: Mapped[str] = mapped_column(String,nullable=True)
    furry_name: Mapped[str] = mapped_column(String,nullable=True)
    type: Mapped[str] = mapped_column(String,nullable=True)
    message: Mapped[str | None] = mapped_column(String,nullable=True)
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=True)


class FurryModifyRequest(Model):
    """图片修改审核队列（原 data/furry_system/upload/upload/modify.json）"""
    __tablename__ = "furry_modify_request"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    picture_id: Mapped[str] = mapped_column(String,nullable=False)
    attr: Mapped[str] = mapped_column(String,nullable=False)
    new_value: Mapped[str | None] = mapped_column(String,nullable=True)
    file_path: Mapped[str | None] = mapped_column(String,nullable=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey(Users.id),nullable=True)
    group_id: Mapped[str | None] = mapped_column(ForeignKey(Groups.id), nullable=True)
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=True)


class FurryPictureData(Model):
    __tablename__ = "furry_picture_data"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey(Users.id),nullable=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey(Groups.id), nullable=True)
    file_path: Mapped[str] = mapped_column(String,nullable=True)
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=True)
    file_name: Mapped[str] = mapped_column(String,nullable=True)
    furry_name: Mapped[str] = mapped_column(String,nullable=True)
    type: Mapped[str] = mapped_column(String,nullable=True)
    description: Mapped[str | None] = mapped_column(String,nullable=True)

async def add_furry_picture(session, uploader_id: str, group_id: int, file_path: str, file_name: str, furry_name: str, type: str, description: str):
    new_picture = FurryPictureData(
        uploader_id=uploader_id,
        group_id=group_id,
        file_path=str(file_path),
        file_name=file_name,
        furry_name=furry_name,
        type=type,
        description=description
    )
    session.add(new_picture)
    await session.commit()

async def update_furry_picture(
        session: async_scoped_session,
        picture_id: int,
        attr: str,
        new_value: str,
        picture: Path | bool
) -> bool:
    picture_db = await session.get(FurryPictureData, picture_id)

    if picture_db is None:
        return False

    if attr == "名字":
        picture_db.furry_name = new_value

    elif attr == "图片类型":
        picture_db.type = new_value
    elif attr == "图片":
        picture_db.file_path = str(picture)
        if picture:
            picture_db.file_name = os.path.basename(picture)
    elif attr == "图片留言":
        if new_value == " " or new_value == "无":
            picture_db.description = None
        else:
            picture_db.description = new_value
    else:
        return False

    await session.commit()
    return True


async def add_upload_request(
        session: async_scoped_session,
        uploader_id: str,
        group_id: str,
        file_path: str,
        file_name: str,
        furry_name: str,
        type: str,
        message: str | None
) -> None:
    """投图入审核队列（原 manifest.json 追加）。"""
    session.add(FurryUploadRequest(
        uploader_id=uploader_id,
        group_id=group_id,
        file_path=file_path,
        file_name=file_name,
        furry_name=furry_name,
        type=type,
        message=message
    ))
    await session.commit()


async def list_upload_requests(session: async_scoped_session) -> list[FurryUploadRequest]:
    """按入队顺序返回全部待审核投图。"""
    result = await session.execute(select(FurryUploadRequest).order_by(FurryUploadRequest.id))
    return list(result.scalars().all())


async def add_modify_request(
        session: async_scoped_session,
        picture_id: str,
        attr: str,
        new_value: str | None,
        file_path: str | None,
        uploader_id: str,
        group_id: str
) -> None:
    """图片修改请求入审核队列（原 modify.json 追加）。"""
    session.add(FurryModifyRequest(
        picture_id=picture_id,
        attr=attr,
        new_value=new_value,
        file_path=file_path,
        uploader_id=uploader_id,
        group_id=group_id
    ))
    await session.commit()


async def list_modify_requests(session: async_scoped_session) -> list[FurryModifyRequest]:
    """按入队顺序返回全部待审核修改请求。"""
    result = await session.execute(select(FurryModifyRequest).order_by(FurryModifyRequest.id))
    return list(result.scalars().all())