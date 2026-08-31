from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users, Groups


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

async def add_furry_picture(session, uploader_id: str, group_id: int, file_path: str, file_name: str, furry_name: str, type: str):
    new_picture = FurryPictureData(
        uploader_id=uploader_id,
        group_id=group_id,
        file_path=str(file_path),
        file_name=file_name,
        furry_name=furry_name,
        type=type
    )
    session.add(new_picture)
    await session.commit()