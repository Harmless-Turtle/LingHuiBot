from datetime import date, timedelta

import nonebot
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import get_session
from sqlalchemy import select, func, desc

from .models import UserGroupUsage, GroupSettings, UserBirthday

driver = nonebot.get_driver()


@driver.on_startup
async def setup_birthday_scheduler():
    _ = scheduler.add_job(
        _init_birthday_jobs,
        "cron",
        hour=9,
        minute=10,
    )


async def _init_birthday_jobs():
    since = date.today() - timedelta(days=6)
    today = date.today()

    # 将CTE定义转换为子查询
    subquery = (
        select(
            UserGroupUsage.user_id,
            UserGroupUsage.group_id,
            func.dense_rank().over(
                partition_by=UserGroupUsage.user_id,
                order_by=desc(func.sum(UserGroupUsage.usage_count)),
            ).label("rnk")
        )
        .join(UserBirthday, UserBirthday.user_id == UserGroupUsage.user_id)
        .join(GroupSettings, GroupSettings.group_id == UserGroupUsage.group_id)
        .where(
            # 过滤今天生日的用户
            func.extract("month", UserBirthday.birthday_date) == today.month,
            func.extract("day", UserBirthday.birthday_date) == today.day,
            # 过滤最近7天的发言
            UserGroupUsage.day >= since,
            # 过滤启用了生日祝福的群组
            GroupSettings.enable.is_(True)
        )
        .group_by(UserGroupUsage.user_id, UserGroupUsage.group_id)
        .subquery("ranked_birthday_users")
    )

    # 查询排名为 1 的群
    targets_stmt = (
        select(subquery.c.user_id, subquery.c.group_id)
        .where(subquery.c.rnk == 1)
    )

    async with get_session() as session:
        result = (await session.execute(targets_stmt)).tuples().all()

    bot = get_bot()
    for user_id, group_id in result:
        try:
            uid = int(user_id)
            gid = int(group_id)
        except (TypeError, ValueError):
            continue
        message = Message(MessageSegment.at(uid) + MessageSegment.text(" 生日快乐！"))
        await bot.send_group_msg(group_id=gid, message=message)
