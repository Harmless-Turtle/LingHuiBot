__import__("nonebot").require("nonebot_plugin_orm")
from typing import Annotated

from nonebot.adapters import Event
from nonebot.params import Depends
from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


def get_group_id(event: Event) -> str:
    return str(event.group_id)


def get_user_id(event: Event) -> str:
    return event.get_user_id()


class Users(Model):
    __tablename__ = "users"
    id: Annotated[Mapped[str], Depends(get_user_id)] = mapped_column(primary_key=True)


class Groups(Model):
    __tablename__ = "groups"
    id: Annotated[Mapped[str], Depends(get_group_id)] = mapped_column(primary_key=True)
