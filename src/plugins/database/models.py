from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class Users(Model):
    id: Mapped[str] = mapped_column(primary_key=True)


class Groups(Model):
    id: Mapped[str] = mapped_column(primary_key=True)
