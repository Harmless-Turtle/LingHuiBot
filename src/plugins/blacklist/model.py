from nonebot_plugin_orm import Model
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped


class UserBlacklist(Model):
    user_id: Mapped[str] = mapped_column(String(20), primary_key=True)

    __table_args__ = (
        UniqueConstraint("user_id", name="user_blacklist_uc"),
    )

class GroupBlacklist(Model):
    group_id: Mapped[str] = mapped_column(String(20), primary_key=True)

    __table_args__ = (
        UniqueConstraint("group_id", name="group_blacklist_uc"),
    )
