from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.plugins.database.models import Users, Groups


class FurryPictureData(Model):
    __tablename__ = "furry_picture_data"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uploader_id: Mapped[str] = mapped_column(ForeignKey(Users.id))
    local_path: Mapped[str] = mapped_column(String)
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime,default=datetime.now)
    group_id: Mapped[int | None] = mapped_column(ForeignKey(Groups.id),nullable=True)
    review_status: Mapped[bool] = mapped_column(default=False)