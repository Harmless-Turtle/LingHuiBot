from datetime import datetime
from types import SimpleNamespace

from nonebot_plugin_orm import Model, async_scoped_session
from sqlalchemy import DateTime, ForeignKey, Integer, select
from sqlalchemy.orm import Mapped, mapped_column

from ..database.models import Groups, Users
from ..utils import utc_now
from .exceptions import AlreadySignedToday, SignInError


# ============================================================
#                       签到系统
#   原 data/main/sign_in/sign_in.json
#   拆分为两张表：群级别每日计数 + 个人每月签到记录
#   时间一律存标准 UTC（naive datetime），业务层按需 +8 小时转本地
# ============================================================

class SignInGroup(Model):
    """群级别签到状态：记录该群最近一次签到时间与当日已签到人数。"""
    __tablename__ = "sign_in_group"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    # 最近一次签到时间（标准 UTC）；跨日时重置当日计数
    last_sign_in_at: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    # 当日已签到人数，跨日时重置
    daily_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SignInUser(Model):
    """个人在某群的签到记录：本月签到次数与最近一次签到时间（标准 UTC）。"""
    __tablename__ = "sign_in_user"
    group_id: Mapped[str] = mapped_column(ForeignKey(Groups.id), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(Users.id), primary_key=True)
    # 本月签到次数，跨月重置
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 最近一次签到时间：标准 UTC（naive），业务层按需 +8 小时转本地
    last_sign_in_at: Mapped[datetime] = mapped_column(DateTime(), nullable=True)


async def do_sign_in(
        session: async_scoped_session,
        group_id: str,
        user_id: str,
) -> SimpleNamespace:
    """
    执行一次签到，等价于原 sign_in.json 的读-改-写流程。

    - 当日已签到：抛出 AlreadySignedToday（SignInError 子类）
    - 返回 SimpleNamespace：
        - user_count:  个人本月签到次数（签到后）
        - group_count: 今日群内签到排名（签到后）
        - prev_sign_in_at: 签到前的上次签到时间（UTC datetime；新用户为 None）
        - sign_in_at:      本次签到时间（UTC datetime）

    数据库异常统一转换为 SignInError（并 rollback 清除脏会话），由上层 handler 捕获。
    """
    try:
        now_utc = utc_now()

        # ---- 群级别记录：取或建 ----
        g_res = await session.execute(select(SignInGroup).where(SignInGroup.group_id == group_id))
        group_row = g_res.scalar_one_or_none()
        if group_row is None:
            group_row = SignInGroup(group_id=group_id, last_sign_in_at=None, daily_count=0)
            session.add(group_row)
            await session.flush()

        # 跨日则重置当日计数
        if group_row.last_sign_in_at is None or group_row.last_sign_in_at.date() != now_utc.date():
            group_row.last_sign_in_at = now_utc
            group_row.daily_count = 0

        # ---- 个人记录：取或建 ----
        u_res = await session.execute(
            select(SignInUser).where(
                SignInUser.group_id == group_id,
                SignInUser.user_id == user_id,
            )
        )
        user_row = u_res.scalar_one_or_none()
        prev_sign_in_at = None
        if user_row is None:
            user_row = SignInUser(group_id=group_id, user_id=user_id, count=0, last_sign_in_at=None)
            session.add(user_row)
            await session.flush()
        else:
            prev_sign_in_at = user_row.last_sign_in_at

        # 今日已签到：抛业务异常，由上层 handler 统一反馈
        if prev_sign_in_at is not None and prev_sign_in_at.date() == now_utc.date():
            raise AlreadySignedToday()

        # 跨月则重置个人本月计数
        if prev_sign_in_at is None or prev_sign_in_at.month != now_utc.month:
            user_row.count = 0

        user_row.count += 1
        user_row.last_sign_in_at = now_utc
        group_row.daily_count += 1
        await session.flush()

        return SimpleNamespace(
            user_count=user_row.count,
            group_count=group_row.daily_count,
            prev_sign_in_at=prev_sign_in_at,
            sign_in_at=now_utc,
        )
    except SignInError:
        raise
    except Exception as e:
        # 捕获数据库异常：回滚清除脏会话，防止会话污染
        await session.rollback()
        raise SignInError() from e
