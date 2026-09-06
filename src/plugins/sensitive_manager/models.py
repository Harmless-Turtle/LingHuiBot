from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..database.models import Groups, Users


# ============================================================
#                       敏感词系统
#   原 data/sensitive_manager/ 下的三个 JSON：
#     sensitive_data.json    -> {group: {words:[...], admin:[...]}}
#     group_settings.json    -> {group: bool}
#     user_violations.json   -> {group: {user: {count, warnings, records:[{time,content}]}}}
# ============================================================

class SensitiveGroupSetting(Model):
    """每个群的敏感词检测开关。"""
    __tablename__ = "sensitive_group_setting"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SensitiveWord(Model):
    """每个群的敏感词，一行一词。"""
    __tablename__ = "sensitive_word"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    word: Mapped[str] = mapped_column(String, primary_key=True)


class SensitiveGroupAdmin(Model):
    """每个群首次添加敏感词的操作者，作为该群的敏感词管理员。"""
    __tablename__ = "sensitive_group_admin"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)


class SensitiveViolation(Model):
    """用户在某群的违规记录，records 以 JSON 文本保存历史明细。"""
    __tablename__ = "sensitive_violation"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records: Mapped[str] = mapped_column(Text, default="[]", nullable=False)


async def load_sensitive_words(session: async_scoped_session) -> dict[str, dict]:
    """返回 {group_id: {"words": set(), "admin": [user_id, ...]}}。"""
    words_res = await session.execute(select(SensitiveWord))
    admins_res = await session.execute(select(SensitiveGroupAdmin))

    data: dict[str, dict] = {}
    for row in words_res.all():
        gid, word = row[0], row[1]
        data.setdefault(gid, {"words": set(), "admin": []})["words"].add(word)
    for row in admins_res.all():
        gid, uid = row[0], row[1]
        data.setdefault(gid, {"words": set(), "admin": []})["admin"].append(uid)
    return data


async def load_sensitive_settings(session: async_scoped_session) -> dict[str, bool]:
    res = await session.execute(select(SensitiveGroupSetting))
    return {row[0]: bool(row[1]) for row in res.all()}


async def set_sensitive_enabled(
        session: async_scoped_session, group_id: str, enabled: bool
) -> None:
    res = await session.execute(
        select(SensitiveGroupSetting).where(SensitiveGroupSetting.group_id == group_id)
    )
    setting = res.scalar_one_or_none()
    if setting is None:
        setting = SensitiveGroupSetting(group_id=group_id, enabled=enabled)
        session.add(setting)
    else:
        setting.enabled = enabled
    await session.flush()


async def add_sensitive_word(
        session: async_scoped_session, group_id: str, word: str
) -> None:
    session.add(SensitiveWord(group_id=group_id, word=word))
    await session.flush()


async def remove_sensitive_word(
        session: async_scoped_session, group_id: str, word: str
) -> bool:
    """删除指定敏感词，返回其原先是否存在。"""
    res = await session.execute(
        select(SensitiveWord).where(
            SensitiveWord.group_id == group_id,
            SensitiveWord.word == word,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def add_sensitive_admin(
        session: async_scoped_session, group_id: str, user_id: str
) -> None:
    res = await session.execute(
        select(SensitiveGroupAdmin).where(
            SensitiveGroupAdmin.group_id == group_id,
            SensitiveGroupAdmin.user_id == user_id,
        )
    )
    if res.scalar_one_or_none() is None:
        session.add(SensitiveGroupAdmin(group_id=group_id, user_id=user_id))
        await session.flush()


async def get_violation(
        session: async_scoped_session, group_id: str, user_id: str
) -> SensitiveViolation:
    """获取违规记录，不存在则创建空记录。"""
    res = await session.execute(
        select(SensitiveViolation).where(
            SensitiveViolation.group_id == group_id,
            SensitiveViolation.user_id == user_id,
        )
    )
    v = res.scalar_one_or_none()
    if v is None:
        v = SensitiveViolation(
            group_id=group_id, user_id=user_id,
            count=0, warnings=0, records="[]",
        )
        session.add(v)
        await session.flush()
    return v


async def delete_violation(
        session: async_scoped_session, group_id: str, user_id: str
) -> None:
    res = await session.execute(
        select(SensitiveViolation).where(
            SensitiveViolation.group_id == group_id,
            SensitiveViolation.user_id == user_id,
        )
    )
    v = res.scalar_one_or_none()
    if v is not None:
        await session.delete(v)
        await session.flush()
