from datetime import date

import nonebot
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_apscheduler import scheduler
from sqlalchemy import select
from nonebot_plugin_orm import get_session

from .models import GroupSettings, UserBirthdayData


driver = nonebot.get_driver()


@driver.on_startup
async def setup_birthday_scheduler():
    _ = scheduler.add_job(
        _init_birthday_jobs,
        "cron",
        hour=7,
        minute=1,
        second=0,
        id="birthday:init",
        misfire_grace_time=120,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )


async def _init_birthday_jobs():
    # 1. 获取 Bot 实例
    try:
        bot = nonebot.get_bot()
    except Exception:
        return

    async with get_session() as session:
        # 2. 查询所有设置了生日的用户
        users = (await session.scalars(select(UserBirthdayData))).all()
    today = date.today()

    for user_birthday in users:
        # 从数据库取的 datetime.date 对象
        b_date = user_birthday.birthday_date
        if not b_date:
            continue

        # 判断今天是否是该用户的生日
        if b_date.month == today.month and b_date.day == today.day:
            user_id = user_birthday.user_id

            # 4. 扫描所有开启了功能的群组发送祝贺
            group_settings = await session.get(GroupSettings, user_birthday.group_id)

            if group_settings and group_settings.enable:
                try:
                    group_user_list = await bot.get_group_member_list(group_id=str(group_settings.group_id))
                    if int(user_id) not in [member['user_id'] for member in group_user_list]:
                        continue  # 不在群内，直接跳过当前用户，不发消息
                    # 获取昵称
                    stranger_info = await bot.get_stranger_info(user_id=int(user_id))
                    nickname = stranger_info.get('nickname', '小寿星')

                    # 计算年龄（如果是1900年则不显示岁数）
                    age_text = f"今天是群里 {nickname} 的生日嗷呜！"
                    if b_date.year != 1900:
                        age = today.year - b_date.year
                        if age > 0:
                            age_text = f"今天是 {nickname} 的 {age} 岁生日！"

                    # 发送群消息
                    await bot.send_group_msg(
                        group_id=int(group_settings.group_id),
                        message=MessageSegment.at(user_id) + f" {age_text}\n祝{nickname}生日快乐呢~\n"
                    )
                except Exception:
                    continue